"""O dia útil da Capivara Asset, etapa por etapa (veja IDEIA.md).

Herança 07h → Extração 08h → Dashboards 09h → Comitê 10h → Fundo 18h → Empresa 18h30 → Verificações 19h

Cada etapa só enxerga o que a anterior entregou e grava no rastro (gestora/rastro.py) as entradas, a regra, a conta
e a origem de cada número. As falas da ata saem do rastro. Tudo é determinístico: dado o estado de ontem, as séries
reais, as políticas e a diretriz do dia, o resultado é sempre o mesmo. O único acaso é o teste de estresse da
Extração, com semente derivada da data (e do cenário), e cada sorteio aparece no rastro com a chance e o número.
"""
from __future__ import annotations

import copy
import math
import random
import statistics
from datetime import date, timedelta

from . import calendario, config, times as times_, verificacoes
from .mercado import Mercado
from .rastro import Rastro, brl, cel, data, dm, mes, mi, mil, n_, num, pct, pp

VERSAO_MOTOR = 2
AREAS = {"extracao": "Extração", "dashboards": "Dashboards", "executivos": "Executivos", "fundo": "Fundo"}
ETAPAS = [("heranca", "07:00", "Herança"), ("extracao", "08:00", "Extração"), ("dashboards", "09:00", "Dashboards"),
          ("comite", "10:00", "Comitê"), ("fundo", "18:00", "Fundo"), ("empresa", "18:30", "Empresa"),
          ("verificacoes", "19:00", "Verificações")]

PROB_RESOLVER = {
    # (tipo, ação) -> chance diária de o incidente simulado se resolver
    ("atraso", "aguardar"): 0.6, ("atraso", "fonte_alternativa"): 0.6, ("atraso", "corrigir_conector"): 0.9,
    ("atraso", "escalar"): 0.6,
    ("fora_do_ar", "aguardar"): 0.25, ("fora_do_ar", "fonte_alternativa"): 0.25, ("fora_do_ar", "corrigir_conector"): 0.45,
    ("fora_do_ar", "escalar"): 0.25,
}
PESOS_TIPO = {"atraso": 50, "fora_do_ar": 35, "mudanca_formato": 15}
DIVIDA = {"inicial": 35.0, "deriva_dia": 0.45, "por_incidente": 0.7, "abate_por_mil": 1.0}
COTISTAS_PADRAO = {"captacao_base": 0.0001, "sens_desempenho": 0.15, "sens_credibilidade": 0.002,
                   "credibilidade_neutra": 0.75, "limite": 0.03, "janela": 21}
CREDIBILIDADE = {"inicial": 0.85, "acerto": 0.01, "erro": 0.05, "sens_confianca": 0.02, "confianca_alvo": 0.95}
TOLERANCIA_DIVERGENCIA = 0.005
Z_ATIPICO = 4.0


def rng(d: date, *nomes: str) -> random.Random:
    prefixo = [config.SEMENTE] if config.SEMENTE else []  # o experimento mantém as sementes de sempre
    return random.Random(":".join([*prefixo, d.isoformat(), *nomes]))


def semente(d: date, *nomes: str) -> str:
    prefixo = [config.SEMENTE] if config.SEMENTE else []
    return ":".join([*prefixo, d.isoformat(), *nomes])


def _cotistas(politicas: dict) -> dict:
    return {**COTISTAS_PADRAO, **politicas["fundo"].get("cotistas", {})}


def _estresse(politicas: dict) -> dict:
    return {"ativo": True, "multiplicador": 1.0, **politicas["extracao"].get("estresse", {})}


# ====================================================================== preços (administrador do fundo)
def cotacao(mercado: Mercado, ativo: str, d: date, titulo: str | None) -> dict | None:
    """Preço oficial de marcação do ativo no dia `d` (ou o último antes dele). O administrador do fundo tem os
    preços mesmo quando a Extração da gestora está com problema."""
    if ativo == "caixa":
        return {"preco": 1.0, "data": d.isoformat(), "titulo": None, "serie": "cdi", "fonte": "CDI"}
    if ativo in config.TITULOS:
        tipo, anos = config.TITULOS[ativo]
        if titulo is None or titulo <= d.isoformat() or not mercado.titulo(tipo, titulo, d):
            titulo = mercado.escolher_titulo(tipo, anos, d)
        h = mercado.titulo(tipo, titulo, d) if titulo else None
        if not h:
            return None
        return {"preco": h[2], "data": h[0], "titulo": titulo, "serie": "tesouro", "fonte": "Tesouro Direto",
                "taxa": h[1], "rotulo": f"{tipo} {titulo[:4]}"}
    serie, alt = {"dolar": ("dolar", "dolar_ptax"), "bolsa": ("bova11", "bova11_b3")}[ativo]
    u, a = mercado.ultimo(serie, d), mercado.ultimo(alt, d)
    escolhido, s = (u, serie) if u and (not a or u[0] >= a[0]) else (a, alt)
    if not escolhido:
        return None
    fonte = {"dolar": "BCB SGS", "dolar_ptax": "BCB PTAX", "bova11": "Yahoo", "bova11_b3": "B3 COTAHIST"}[s]
    return {"preco": escolhido[1], "data": escolhido[0], "titulo": None, "serie": s, "fonte": fonte,
            "rotulo": {"dolar": "Dólar PTAX", "bolsa": "BOVA11"}[ativo]}


def _fator_cdi(mercado: Mercado, inicio: date, fim: date) -> tuple[float, list]:
    fator, dias = 1.0, []
    for d in calendario.dias_uteis_entre(inicio, fim):
        u = mercado.ultimo("cdi", d)
        taxa = u[1] if u else 0.05
        fator *= 1 + taxa / 100
        dias.append((d.isoformat(), taxa, u[0] if u else None))
    return fator, dias


# ====================================================================== estado inicial
def _ultima_ate(mercado: Mercado, serie: str, d: date) -> str | None:
    if serie == "tesouro":
        datas = [h for h in (mercado.titulo(t, v, d) for (t, v) in mercado.tesouro()) if h]
        return max((h[0] for h in datas), default=None)
    u = mercado.ultimo(serie, d)
    return u[0] if u else None


def estado_inicial(inicio: date, politicas: dict, mercado: Mercado) -> dict:
    g, f = politicas["gestora"], politicas["fundo"]
    estado = {
        "versao": VERSAO_MOTOR,
        "inicio": inicio.isoformat(),
        "ultima_data": inicio.isoformat(),
        "seq_incidente": 0,
        "extracao": {
            "divida_tecnica": DIVIDA["inicial"],
            "equipe": g["equipe_extracao_inicial"],
            "orcamento_dia": g["orcamento_extracao_dia_inicial"],
            "fontes": {fo: {"liberado_ate": {}, "alternativa_ligada": False} for fo in config.FONTES},
        },
        "incidentes": [],
        "alertas": {},
        "dashboards": {"credibilidade": CREDIBILIDADE["inicial"], "confianca_media": 1.0, "indicadores": {},
                       "estimativas": []},
        "executivos": {"alvo": dict(f["alocacao_inicial"]), "ultima_decisao": None, "dias_sem_decisao": 0,
                       "decisoes_recentes": [], "congelados": []},
        "fundo": {"cota": 1.0, "cotas": float(f["pl_inicial"]), "pl": float(f["pl_inicial"]), "bench": 1.0,
                  "posicoes": {}, "fluxo_dia": 0.0, "retorno_dia": 0.0,
                  "hist_cota": [[inicio.isoformat(), 1.0, 1.0]]},
        "referencia": {"cota": 1.0, "cotas": float(f["pl_inicial"]), "posicoes": {}},
        "gestora": {"caixa": float(g["caixa_inicial"]), "receita_dia": 0.0, "custo_dia": 0.0},
        "times": {"erros": {}, "comite": {"ultimo": None, "contratou": None}},
        "metricas": {"dias": 0, "dias_em_dia": 0, "incidentes_simulados": 0, "incidentes_reais": 0, "resolvidos": 0,
                     "dias_resolucao": 0, "estimativas_ok": 0, "estimativas_erro": 0, "verificacoes_ok": 0,
                     "verificacoes_falha": 0, "falhas": [], "reunioes": 0, "mudancas_alvo": 0, "giro": 0.0,
                     "custo_giro": 0.0, "taxa": 0.0, "fluxo": 0.0},
    }
    for fonte in config.FONTES:
        for serie in config.FONTES[fonte]["series"]:
            estado["extracao"]["fontes"][fonte]["liberado_ate"][serie] = _ultima_ate(mercado, serie, corte(serie, inicio)[0])
    fundacao = []
    for ativo, w in f["alocacao_inicial"].items():
        valor = f["pl_inicial"] * w
        c = cotacao(mercado, ativo, inicio, None) or {"preco": None, "data": None, "titulo": None, "serie": None,
                                                     "fonte": None}
        pos = {"valor": valor, "preco": c["preco"], "titulo": c["titulo"], "data_preco": c["data"], "serie": c["serie"]}
        estado["fundo"]["posicoes"][ativo] = pos
        estado["referencia"]["posicoes"][ativo] = dict(pos)
        fundacao.append({"ativo": ativo, "peso": w, "valor": valor, "preco": c["preco"], "data": c["data"],
                         "instrumento": c.get("rotulo") or config.ATIVOS[ativo], "fonte": c["fonte"]})
    estado["fundacao"] = {"data": inicio.isoformat(), "pl": float(f["pl_inicial"]), "posicoes": fundacao,
                          "equipe": g["equipe_extracao_inicial"], "orcamento_dia": g["orcamento_extracao_dia_inicial"],
                          "divida_tecnica": DIVIDA["inicial"], "credibilidade": CREDIBILIDADE["inicial"],
                          "caixa_gestora": float(g["caixa_inicial"]), "taxa_adm": f["taxa_adm"]}
    return estado


# ====================================================================== 07h · Herança
def _etapa_heranca(rastro: Rastro, estado: dict, d: date, anterior: date, numero: int) -> None:
    e = rastro.etapa("heranca", "fundo", "07:00", "Herança", "De onde partimos hoje?")
    f, ex, db, exe = estado["fundo"], estado["extracao"], estado["dashboards"], estado["executivos"]
    pesos = _pesos(f["posicoes"])
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    primeiro = anterior.isoformat() == estado["inicio"]
    linhas = [
        ["Ponto de partida", "fundação da empresa" if primeiro else "fechamento do dia útil anterior", data(anterior)],
        ["Cota do fundo", num(f["cota"], 6), f"patrimônio {mi(f['pl'])}"],
        ["Carteira (peso atual → alvo)", ", ".join(f"{config.ATIVOS[a].split(' (')[0]} {pct(pesos[a], 1)}→{pct(exe['alvo'][a], 0)}"
                                                   for a in exe["alvo"]), "o alvo só muda em reunião do comitê"],
        ["Equipe de Extração", f"{n_(ex['equipe'], 'pessoa')} = {n_(ex['equipe'], 'ponto')}/dia",
         f"orçamento {brl(ex['orcamento_dia'])}/dia"],
        ["Dívida técnica", f"{num(ex['divida_tecnica'], 1)}/100", "quanto maior, mais as fontes falham no teste de estresse"],
        ["Incidentes abertos", ", ".join(f"{i['id']} ({config.FONTES[i['fonte']]['nome']}, {i['tipo']}, {n_(i['dias'], 'dia')})"
                                         for i in abertos) or "nenhum", ""],
        ["Credibilidade dos painéis", pct(db["credibilidade"], 1), f"{n_(len(db['estimativas']), 'estimativa')} a conferir"],
        ["Caixa da gestora", brl(estado["gestora"]["caixa"]), "a empresa, não o fundo"],
    ]
    b = e.tabela("O que veio do fechamento anterior", ["Item", "Valor", "Observação"], linhas, origem="simulado")
    if primeiro and estado.get("fundacao"):
        fu = estado["fundacao"]
        e.tabela(f"Fundação em {data(fu['data'])}: a carteira comprada no primeiro dia", [
            "Ativo", "Peso", "Valor", "Instrumento", "Preço de compra", "Data do preço", "Fonte"],
            [[config.ATIVOS[p["ativo"]], pct(p["peso"], 0), mi(p["valor"]), p["instrumento"],
              cel(num(p["preco"], 4 if p["ativo"] == "dolar" else 2) if p["preco"] else "—", "real"),
              data(p["data"]), p["fonte"] or "—"] for p in fu["posicoes"]],
            nota=f"Patrimônio inicial {mi(fu['pl'])}, cota 1,000000. Caixa da gestora {brl(fu['caixa_gestora'])}, "
                 f"equipe de {fu['equipe']}, dívida técnica {num(fu['divida_tecnica'], 0)}, credibilidade "
                 f"{pct(fu['credibilidade'], 0)}.")
    e.status("info", f"dia útil nº {numero} desde a fundação em {data(estado['inicio'])}"
             + (f" · {n_(len(abertos), 'incidente herdado', 'incidentes herdados')}" if abertos else ""))
    e.dados["bloco_principal"] = b


# ====================================================================== 08h · Extração
def corte(serie: str, d: date) -> tuple[date, date]:
    """(até que data a série pode ser vista às 08h de `d`, data que uma fonte em dia já teria publicado)."""
    return calendario.corte_publicacao(config.PUBLICACAO[serie], d)


def _real_por_fonte(mercado: Mercado, fonte: str, d: date, controle: dict | None) -> dict:
    """O que a fonte real tinha publicado até `d` (e, no experimento, se o conector funcionou hoje)."""
    ctrl = (controle or {}).get("fontes", {}).get(fonte)
    out = {"ok": True, "motivo": "", "series": [], "conector": ctrl}
    if ctrl and ctrl.get("status") == "erro":
        out["ok"], out["motivo"] = False, ctrl.get("erro") or "erro no conector"
    for serie in config.FONTES[fonte]["series"]:
        ate, esperada = corte(serie, d)
        ultima = _ultima_ate(mercado, serie, ate)
        em_dia = ultima is not None and ultima >= esperada.isoformat()
        out["series"].append({"serie": serie, "esperada": esperada.isoformat(), "ultima": ultima, "em_dia": em_dia})
        if not em_dia and out["ok"]:
            out["ok"], out["motivo"] = False, f"série {serie} parada em {data(ultima)} (esperado {data(esperada.isoformat())})"
    return out


def _novo_incidente(estado: dict, fonte: str, tipo: str, d: date, detalhe: str) -> dict:
    estado["seq_incidente"] += 1
    inc = {"id": f"INC-{estado['seq_incidente']:04d}", "fonte": fonte, "tipo": tipo, "aberto_em": d.isoformat(),
           "estado": "aberto", "dias": 0, "esforco": 0, "acao": None, "detalhe": detalhe, "resolvido_em": None,
           "origem": "real" if tipo == "falha_real" else "simulado", "historico": []}
    estado["incidentes"].append(inc)
    m = estado["metricas"]
    m["incidentes_reais" if tipo == "falha_real" else "incidentes_simulados"] += 1
    return inc


def _etapa_extracao(rastro: Rastro, estado: dict, d: date, mercado: Mercado, controle: dict | None, politicas: dict,
                    intervencao: dict, eventos: list, modo: str) -> dict:
    e = rastro.etapa("extracao", "extracao", "08:00", "Extração", "Que dados chegaram e quais a empresa pode usar hoje?")
    ex = estado["extracao"]
    padrao = politicas["extracao"]["acao_padrao"]
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]

    # 1) triagem dos incidentes herdados (o time decide); `dias` conta os dias úteis desde a abertura
    for inc in abertos:
        inc["dias"] += 1
    acoes = times_.extracao(e, estado, intervencao)
    for inc in abertos:
        acao = acoes.get(inc["id"], inc["acao"])
        if acao != inc["acao"]:
            inc["historico"].append(f"{d}: ação → {acao}")
        inc["acao"] = acao
        if acao == "escalar":
            estado["alertas"].setdefault(f"ESCALA-{inc['id']}", {
                "titulo": f"Extração pede reforço para {inc['id']} ({config.FONTES[inc['fonte']]['nome']})",
                "area": "executivos", "sev": "media", "aberto_em": d.isoformat(),
                "corpo": "A equipe de Extração não tem pontos livres para tratar o incidente. O comitê avalia "
                         "contratar na reunião das 10h."})

    # 2) o que as fontes reais publicaram até hoje
    real = {f: _real_por_fonte(mercado, f, d, controle) for f in config.FONTES}
    linhas = []
    for fonte, r in real.items():
        for s in r["series"]:
            situacao = "em dia" if s["em_dia"] else "NÃO publicou o esperado"
            linha = [config.FONTES[fonte]["nome"], config.SERIES_INFO[s["serie"]][0],
                     config.REGRA_PUBLICACAO[config.PUBLICACAO[s["serie"]]], data(s["esperada"]),
                     cel(data(s["ultima"]), "real"), cel(situacao, "real")]
            if controle:
                c = r["conector"] or {}
                linha.append(cel(("ok" if c.get("status") == "ok" else f"falhou: {c.get('erro')}") if c else "—", "real"))
            linhas.append(linha)
    colunas = ["Fonte", "Série", "Quando publica", "Esperado", "Publicado até as 08h", "Situação"] + (
        ["Conector na extração real"] if controle else [])
    if modo == "simulacao":
        nota = ("Simulação: as séries de 2026 já foram baixadas das fontes reais; o motor corta cada uma no que estava "
                f"publicado às 08h de {data(d)}. Nada depois disso existe para a empresa neste dia.")
    elif controle:
        nota = (f"Extração real rodada em {controle.get('executado_em', '')[:16].replace('T', ' ')} UTC (janela "
                f"{data(controle['janela'][0])}–{data(controle['janela'][1])}); o motor corta cada série no que "
                f"estava publicado às 08h de {data(d)}.")
    else:
        nota = f"Dia reprocessado com as séries já gravadas, cortadas no que estava publicado às 08h de {data(d)}."
    b_real = e.tabela(f"O que as fontes reais tinham publicado às 08h de {data(d)}", colunas, linhas, nota=nota)
    problemas = [f for f, r in real.items() if not r["ok"]]
    if problemas:
        e.diz(1, "Conferi as 6 fontes reais. Problema de verdade em " + "; ".join(
            f"{config.FONTES[f]['nome']}: {real[f]['motivo']}" for f in problemas) + ".", bloco=b_real, minutos=10,
            tipo="alerta")
    else:
        datas = {}
        for f, r in real.items():
            for s in r["series"]:
                quando = mes(s["ultima"]) if config.PUBLICACAO[s["serie"]] == "mensal" else dm(s["ultima"])
                datas.setdefault((s["ultima"] or "", quando), []).append(config.SERIES_INFO[s["serie"]][2])
        resumo = "; ".join(f"{', '.join(v)} até {q}" for (_, q), v in sorted(datas.items(), reverse=True))
        e.diz(1, f"Conferi as 6 fontes reais: todas em dia ({resumo}).", bloco=b_real, minutos=10)

    # 3) incidentes abertos: resolvem hoje?
    linhas = []
    for inc in abertos:
        fonte, acao = inc["fonte"], inc["acao"]
        alt = times_.tem_alternativa(fonte)
        ex["fontes"][fonte]["alternativa_ligada"] = acao == "fonte_alternativa" and alt
        if acao == "corrigir_conector":
            inc["esforco"] += 1
        if inc["tipo"] == "falha_real":
            resolveu = real[fonte]["ok"]
            chance, sorteio, conta = None, None, "volta quando a fonte real publicar o esperado"
        else:
            if inc["tipo"] == "mudanca_formato":
                chance = (min(0.95, 0.25 * inc["esforco"] + 0.05 * (ex["equipe"] - 3)) if acao == "corrigir_conector"
                          else 0.0)
                conta = (f"0,25 × esforço {inc['esforco']} + 0,05 × (equipe {ex['equipe']} − 3) = {pct(chance, 0)}"
                         if acao == "corrigir_conector" else "só resolve com `corrigir_conector`")
            else:
                chance = PROB_RESOLVER.get((inc["tipo"], acao), 0.3)
                conta = f"tabela ({inc['tipo']}, {acao})"
            sorteio = rng(d, inc["id"]).random()
            resolveu = sorteio < chance
        linhas.append([inc["id"], config.FONTES[fonte]["nome"], inc["tipo"], f"`{acao}`",
                       cel(pct(chance, 0) if chance is not None else "—", "simulado" if chance is not None else "real", conta),
                       cel(num(sorteio, 3) if sorteio is not None else "—", "simulado",
                           f"semente {semente(d, inc['id'])}" if sorteio is not None else None),
                       cel("resolvido" if resolveu else "segue aberto", "simulado" if chance is not None else "real")])
        if resolveu:
            inc["estado"], inc["resolvido_em"] = "resolvido", d.isoformat()
            inc["historico"].append(f"{d}: resolvido ({acao})")
            ex["fontes"][fonte]["alternativa_ligada"] = False
            estado["alertas"].pop(f"ESCALA-{inc['id']}", None)
            estado["metricas"]["resolvidos"] += 1
            estado["metricas"]["dias_resolucao"] += inc["dias"]
            eventos.append(_evento("extracao", "resolvido", f"{inc['id']} resolvido: {config.FONTES[fonte]['nome']} "
                                   f"voltou após {n_(inc['dias'], 'dia')} ({acao})", chave=inc["id"]))
    if linhas:
        b = e.tabela("Incidentes abertos: resolvem hoje?", ["Incidente", "Fonte", "Tipo", "Ação", "Chance hoje",
                     "Sorteio", "Resultado"], linhas,
                     nota="Resolve se o sorteio for menor que a chance. Falha real não tem sorteio: depende da fonte.")
        partes = []
        for ln in linhas:
            if ln[5]["v"] == "—":
                partes.append(f"{ln[0]} ({ln[1]}, falha real): " + ("a fonte voltou a publicar o esperado → resolvido"
                              if ln[6]["v"] == "resolvido" else "a fonte ainda não publicou o esperado → segue aberto"))
            else:
                partes.append(f"{ln[0]} ({ln[1]}, {ln[3]}): chance {ln[4]['v']}, sorteio {ln[5]['v']} → {ln[6]['v']}")
        e.diz(1, "; ".join(partes) + ".", bloco=b, minutos=20,
              tipo="evento" if any(ln[6]["v"] == "resolvido" for ln in linhas) else "fala")

    # 4) falhas reais viram incidente; o teste de estresse sorteia as simuladas
    est = _estresse(politicas)
    linhas, novos = [], []
    for fonte, meta in config.FONTES.items():
        aberto = next((i for i in estado["incidentes"] if i["fonte"] == fonte and i["estado"] == "aberto"), None)
        if not real[fonte]["ok"] and not (aberto and aberto["tipo"] == "falha_real"):
            inc = _novo_incidente(estado, fonte, "falha_real", d, real[fonte]["motivo"])
            inc["acao"] = padrao.get("falha_real", "corrigir_conector")
            novos.append(inc)
            linhas.append([meta["nome"], "—", "—", cel(f"{inc['id']}: falha real", "real")])
            eventos.append(_evento("extracao", "aberto", f"{inc['id']}: falha real em {meta['nome']}", chave=inc["id"]))
            continue
        if aberto:
            linhas.append([meta["nome"], "—", "—", f"não sorteia: {aberto['id']} aberto"])
            continue
        chance = meta["prob_base"] * (1 + ex["divida_tecnica"] / 40) * est["multiplicador"]
        conta = (f"{pct(meta['prob_base'], 1)} × (1 + {num(ex['divida_tecnica'], 1)}/40)"
                 + (f" × {num(est['multiplicador'], 1)}" if est["multiplicador"] != 1 else "") + f" = {pct(chance, 2)}")
        if not est["ativo"]:
            linhas.append([meta["nome"], cel(conta, "simulado"), "—", "teste de estresse desligado"])
            continue
        r = rng(d, "incidente", fonte)
        sorteio = r.random()
        if sorteio < chance:
            tipo = r.choices(list(PESOS_TIPO), weights=list(PESOS_TIPO.values()))[0]
            inc = _novo_incidente(estado, fonte, tipo, d, config.TIPOS_INCIDENTE[tipo])
            inc["acao"] = padrao.get(tipo, "aguardar")
            ex["fontes"][fonte]["alternativa_ligada"] = inc["acao"] == "fonte_alternativa" and times_.tem_alternativa(fonte)
            novos.append(inc)
            resultado = cel(f"{inc['id']}: {tipo} (simulado)", "simulado",
                            f"tipo sorteado com pesos {'/'.join(str(v) for v in PESOS_TIPO.values())}")
            eventos.append(_evento("extracao", "aberto", f"{inc['id']}: {meta['nome']} — {config.TIPOS_INCIDENTE[tipo]} "
                                   "(teste de estresse)", chave=inc["id"]))
        else:
            resultado = cel("sem falha", "simulado")
        linhas.append([meta["nome"], cel(conta, "simulado"),
                       cel(num(sorteio, 3), "simulado", f"semente {semente(d, 'incidente', fonte)}"), resultado])
    b_est = e.tabela("Teste de estresse: sorteio de falhas por fonte", ["Fonte", "Chance de falhar hoje", "Sorteio",
                     "Resultado"], linhas,
                     nota="As fontes reais quase nunca falham. Para a empresa ter os desafios da ideia original, a "
                          "Extração sorteia falhas: chance = base da fonte × (1 + dívida técnica/40). Falha se o "
                          "sorteio for menor que a chance. O dado real existe, mas fica retido enquanto o incidente "
                          "estiver aberto.")
    simulados = [i for i in novos if i["tipo"] != "falha_real"]
    if not est["ativo"]:
        e.diz(1, "Teste de estresse desligado na política: só falhas reais abrem incidente.", bloco=b_est, minutos=30)
    elif simulados:
        partes = []
        for inc in simulados:
            ln = next(x for x in linhas if x[0] == config.FONTES[inc["fonte"]]["nome"])
            partes.append(f"{config.FONTES[inc['fonte']]['nome']} tirou {ln[2]['v']} contra chance de "
                          f"{ln[1]['v'].split('= ')[-1]} → {inc['id']} ({config.TIPOS_INCIDENTE[inc['tipo']]})")
        e.diz(1, f"Teste de estresse com dívida técnica {num(ex['divida_tecnica'], 1)}: " + "; ".join(partes)
              + ". O dado real existe, mas fica retido até resolvermos.", tipo="alerta", bloco=b_est, minutos=30)
    else:
        sorteados = [(x[2]["v"], x[1]["v"].split("= ")[-1], x[0]) for x in linhas if isinstance(x[2], dict)]
        if sorteados:
            folga = min(sorteados, key=lambda s: float(s[0].replace(",", ".")))
            e.diz(1, f"Teste de estresse com dívida técnica {num(ex['divida_tecnica'], 1)}: nenhuma falha simulada hoje "
                     f"(o sorteio mais baixo foi {folga[0]} em {folga[2]}, contra chance de {folga[1]}).", bloco=b_est,
                  minutos=30)

    # 5) o portão: só avança o que vem de fonte sem incidente aberto
    bloqueio = {i["fonte"]: i for i in estado["incidentes"] if i["estado"] == "aberto"}
    linhas = []
    retidas = []
    for fonte, meta in config.FONTES.items():
        for serie in meta["series"]:
            antes = ex["fontes"][fonte]["liberado_ate"].get(serie)
            if fonte in bloqueio:
                situacao = f"retida por {bloqueio[fonte]['id']}"
                if ex["fontes"][fonte]["alternativa_ligada"]:
                    situacao += " (alternativa ligada)"
                retidas.append(serie)
            else:
                ex["fontes"][fonte]["liberado_ate"][serie] = _ultima_ate(mercado, serie, corte(serie, d)[0])
                situacao = "liberada"
            linhas.append([config.SERIES_INFO[serie][0], meta["nome"], cel(data(ex["fontes"][fonte]["liberado_ate"].get(serie)),
                           "real"), cel(situacao, "simulado" if fonte in bloqueio else "real"),
                           "" if fonte in bloqueio else (f"antes {dm(antes)}" if antes != ex["fontes"][fonte]["liberado_ate"].get(serie) else "sem novidade")])
    b_portao = e.tabela("Portão: o que os Dashboards podem usar", ["Série", "Fonte", "Liberada até", "Situação", "Mudou?"],
                        linhas, nota="Enquanto há incidente aberto, a série fica parada na última data liberada, "
                                     "mesmo que o dado real já exista.")

    # 6) dívida técnica
    n_abertos = len(bloqueio)
    antes = ex["divida_tecnica"]
    ex["divida_tecnica"] = round(min(100.0, max(0.0, antes + DIVIDA["deriva_dia"] + DIVIDA["por_incidente"] * n_abertos
                                                - ex["orcamento_dia"] / 1000 * DIVIDA["abate_por_mil"])), 2)
    b_div = e.contas("Dívida técnica", [
        {"rot": "ontem", "expr": "", "valor": num(antes, 2), "o": "simulado"},
        {"rot": "deriva natural", "expr": "todo dia o código envelhece", "valor": f"+{num(DIVIDA['deriva_dia'], 2)}", "o": "regra"},
        {"rot": "incidentes abertos", "expr": f"{n_abertos} × {num(DIVIDA['por_incidente'], 1)}",
         "valor": f"+{num(DIVIDA['por_incidente'] * n_abertos, 2)}", "o": "regra"},
        {"rot": "orçamento", "expr": f"{brl(ex['orcamento_dia'])} ÷ 1.000", "valor": f"−{num(ex['orcamento_dia'] / 1000, 2)}",
         "o": "decisao"},
        {"rot": "hoje", "expr": "entre 0 e 100", "valor": num(ex["divida_tecnica"], 2), "o": "simulado"},
    ])
    total = sum(len(m["series"]) for m in config.FONTES.values())
    e.diz(0, f"Liberado para os Dashboards: {total - len(retidas)} de {total} séries"
          + (f"; retidas: {', '.join(retidas)} ({', '.join(sorted({bloqueio[f]['id'] for f in bloqueio}))})" if retidas else "")
          + f". Dívida técnica {num(antes, 1)} → {num(ex['divida_tecnica'], 1)}.", bloco=b_portao, minutos=40)
    graves = [i for i in bloqueio.values() if i["tipo"] in ("falha_real", "mudanca_formato")]
    if graves:
        e.status("ruim", f"{n_(len(bloqueio), 'incidente aberto', 'incidentes abertos')}, {n_(len(graves), 'grave')} · {total - len(retidas)}/{total} séries liberadas")
    elif bloqueio:
        e.status("aviso", f"{n_(len(bloqueio), 'incidente aberto', 'incidentes abertos')} · {total - len(retidas)}/{total} séries liberadas")
    else:
        e.status("ok", f"fontes no ar · {total}/{total} séries liberadas · dívida técnica {num(ex['divida_tecnica'], 1)}")
    e.dados["bloco_principal"] = b_portao
    # incidentes resolvidos há mais de 30 dias saem do estado (o histórico fica em dados/dias)
    limite = (d - timedelta(days=30)).isoformat()
    estado["incidentes"] = [i for i in estado["incidentes"] if i["estado"] == "aberto" or i["resolvido_em"] >= limite]
    return {"acoes": {i: a for i, a in acoes.items()}, "real": real}


# ====================================================================== 09h · Dashboards
def _calc_indicador(ind: str, mercado: Mercado, ate: str | None, estado: dict, via: str) -> dict | None:
    """Valor do indicador usando só dados até `ate` (o que está liberado), com a conta que o produziu."""
    if ate is None:
        return None
    meta = config.INDICADORES[ind]
    if via == "alternativa":
        af, aserie = meta["alt"]
        u = mercado.ultimo(aserie, ate)
        return {"data": u[0], "valor": u[1], "serie": aserie,
                "conta": f"fonte alternativa {config.FONTES[af]['nome']}: {aserie} de {dm(u[0])}"} if u else None
    if ind == "cdi":
        u = mercado.ultimo("cdi", ate)
        if not u:
            return None
        anual = round(((1 + u[1] / 100) ** 252 - 1) * 100, 2)
        return {"data": u[0], "valor": anual, "serie": "cdi",
                "conta": f"CDI diário {num(u[1], 6)}% de {dm(u[0])} → (1 + {num(u[1], 6)}%)^252 − 1 = {num(anual)}% a.a."}
    if ind == "ipca_12m":
        h = mercado.historico("ipca", ate, 12)
        if len(h) < 12:
            return None
        v = round((math.prod(1 + x / 100 for _, x in h) - 1) * 100, 2)
        return {"data": h[-1][0], "valor": v, "serie": "ipca",
                "conta": f"12 IPCAs mensais ({h[0][0][5:7]}/{h[0][0][:4]} a {h[-1][0][5:7]}/{h[-1][0][:4]}): "
                         f"Π(1 + mensal) − 1 = {num(v)}%"}
    if ind in ("taxa_pre", "taxa_ipca"):
        ativo = meta["ativo"]
        tipo, anos = config.TITULOS[ativo]
        venc = estado["fundo"]["posicoes"].get(ativo, {}).get("titulo")
        if not venc or not mercado.titulo(tipo, venc, ate) or venc <= str(ate):
            venc = mercado.escolher_titulo(tipo, anos, date.fromisoformat(ate))
        h = mercado.titulo(tipo, venc, ate) if venc else None
        if not h:
            return None
        return {"data": h[0], "valor": h[1], "serie": "tesouro",
                "conta": f"{tipo} {venc[:4]} (o título da carteira): taxa de compra de {dm(h[0])}"}
    u = mercado.ultimo(meta["serie"], ate)
    if not u:
        return None
    return {"data": u[0], "valor": u[1], "serie": meta["serie"],
            "conta": f"último valor de {config.SERIES_INFO[meta['serie']][0]} até {dm(ate)}"}


def _estimar(ind: str, base: dict, atraso: int, mercado: Mercado, publicados: dict) -> tuple[float, str]:
    if ind == "cdi":
        sel = publicados.get("selic")
        if sel and sel.get("valor") is not None:
            v = round(sel["valor"] - 0.10, 2)
            return v, f"Selic {num(sel['valor'])}% − 0,10 p.p. = {num(v)}% a.a."
        return base["valor"], "sem Selic: repete o último"
    if ind in ("dolar", "ibov", "bova11"):
        h = mercado.historico(base["serie"], base["data"], 6)
        if len(h) >= 2:
            ret = (h[-1][1] / h[0][1]) ** (1 / (len(h) - 1)) - 1
            v = round(base["valor"] * (1 + ret) ** atraso, 4)
            return v, (f"{num(base['valor'], 4)} × (1 {'+' if ret >= 0 else '−'} {num(abs(ret) * 100, 3)}%/dia)^{atraso} "
                       f"= {num(v, 4)} (tendência de {dm(h[0][0])} a {dm(h[-1][0])})")
    return base["valor"], "repete o último"


def _tendencia(mercado: Mercado, serie: str, ate: str, janela: int) -> dict | None:
    h = mercado.historico(serie, ate, janela + 1)
    if len(h) < janela // 2 + 1:
        return None
    return {"valor": h[-1][1] / h[0][1] - 1, "de": h[0][0], "ate": h[-1][0], "n": len(h) - 1,
            "v_de": h[0][1], "v_ate": h[-1][1]}


def _qualidade(mercado: Mercado, publicados: dict, situacao: dict) -> list[dict]:
    """Checagens reais nos dados liberados: divergência entre fontes e variação atípica."""
    out = []
    for ind, (principal, alt) in {"bova11": ("bova11", "bova11_b3"), "dolar": ("dolar", "dolar_ptax")}.items():
        lib = situacao[ind]["lib"]
        if not lib:
            continue
        a, b = mercado.ultimo(principal, lib), mercado.ultimo(alt, lib)
        if a and b:
            comum = min(a[0], b[0])
            va, vb = mercado.ultimo(principal, comum), mercado.ultimo(alt, comum)
            if va and vb and va[0] == vb[0]:
                dif = va[1] / vb[1] - 1
                out.append({"ind": ind, "checagem": f"{config.SERIES_INFO[principal][2]} × {config.SERIES_INFO[alt][2]} em {dm(va[0])}",
                            "resultado": f"{num(va[1], 4)} × {num(vb[1], 4)} ({pct(dif, 2, True)})",
                            "ok": abs(dif) <= TOLERANCIA_DIVERGENCIA,
                            "regra": f"diferença até {pct(TOLERANCIA_DIVERGENCIA, 1)}"})
    for ind in ("dolar", "ibov", "bova11"):
        pub = publicados.get(ind) or {}
        if pub.get("estrategia") or pub.get("valor") is None:
            continue
        serie = pub.get("serie") or config.INDICADORES[ind]["serie"]
        h = mercado.historico(serie, pub["data_ref"], 22)
        if len(h) < 8:
            continue
        rets = [h[i][1] / h[i - 1][1] - 1 for i in range(1, len(h))]
        ultimo, anteriores = rets[-1], rets[:-1]
        dp = statistics.pstdev(anteriores) or 1e-9
        z = (ultimo - statistics.fmean(anteriores)) / dp
        out.append({"ind": ind, "checagem": f"variação de {config.INDICADORES[ind]['nome'].split(' (')[0]} em {dm(h[-1][0])}",
                    "resultado": f"{pct(ultimo, 2, True)} = {num(z, 1)} desvios-padrão dos {len(anteriores)} anteriores",
                    "ok": abs(z) <= Z_ATIPICO, "regra": f"até {num(Z_ATIPICO, 0)} desvios-padrão",
                    "z": z, "var": ultimo})
    return out


def _etapa_dashboards(rastro: Rastro, estado: dict, d: date, mercado: Mercado, politicas: dict, intervencao: dict,
                      eventos: list) -> dict:
    e = rastro.etapa("dashboards", "dashboards", "09:00", "Dashboards", "Que números vão para o comitê, e com que confiança?")
    db = estado["dashboards"]
    pol = politicas["dashboards"]
    fontes = estado["extracao"]["fontes"]
    janela = times_.modelo(politicas)["janela_tendencia"]

    situacao = {}
    for ind, meta in config.INDICADORES.items():
        lib = fontes[meta["fonte"]]["liberado_ate"].get(meta["serie"])
        via = "principal"
        if meta["alt"] and fontes[meta["fonte"]]["alternativa_ligada"]:
            af, aserie = meta["alt"]
            alt_lib = fontes[af]["liberado_ate"].get(aserie)
            if alt_lib and (lib is None or alt_lib > lib):
                lib, via = alt_lib, "alternativa"
        base = _calc_indicador(ind, mercado, lib, estado, via)
        esperada = corte(meta["serie"], d)[1]
        if meta.get("mensal"):
            atraso = 0 if base and base["data"] >= esperada.isoformat() else 1
        else:
            atraso = calendario.defasagem(date.fromisoformat(base["data"]) if base else None, esperada)
        situacao[ind] = {"lib": lib, "via": via, "base": base, "esperada": esperada.isoformat(), "atraso": atraso}

    linhas: list = []  # preenchidas abaixo; a tabela já existe para as falas apontarem para ela
    b_painel = e.tabela("Painel publicado às 09h", ["Indicador", "Valor", "Referência", "Esperado", "Situação",
                        "De onde vem", "Confiança"], linhas,
                        nota="Confiança: dado em dia 100%; fonte alternativa 90%; repetido 100% − 20 p.p. por dia; "
                             "estimado 60%; suspenso 0%; divergência entre fontes −10 p.p.")
    em_dia = sum(1 for s in situacao.values() if s["atraso"] == 0)
    atrasados = [config.INDICADORES[i]["nome"] for i, s in situacao.items() if s["atraso"] > 0]
    e.diz(0, f"Com o que a Extração liberou, {em_dia} de {len(situacao)} indicadores chegaram com o dado esperado"
          + (f"; atrasados: {', '.join(atrasados)}. Decidimos o que publicar no lugar." if atrasados else "."),
          bloco=b_painel)
    estrategias, _ = times_.dashboards(e, estado, d, {i: s["atraso"] for i, s in situacao.items() if s["atraso"] > 0},
                                       intervencao)
    publicados: dict[str, dict] = {}
    confs = []
    for ind, meta in config.INDICADORES.items():
        s = situacao[ind]
        base = s["base"]
        anterior = db["indicadores"].get(ind, {})
        reg = {"nome": meta["nome"], "data_ref": base["data"] if base else None, "defasagem": s["atraso"],
               "via": s["via"], "estrategia": None, "valor": base["valor"] if base else None,
               "confianca": 1.0 if s["via"] == "principal" else 0.9, "valor_anterior": anterior.get("valor"),
               "serie": base["serie"] if base else None, "conta": base["conta"] if base else "sem dado liberado",
               "esperada": s["esperada"]}
        conta_conf = "dado em dia" if s["via"] == "principal" else "via fonte alternativa"
        origem = "real" if ind in ("selic", "dolar", "ibov", "bova11", "focus_ipca", "focus_selic") else "derivado"
        if s["atraso"] > 0:
            est = estrategias.get(ind) or pol.get("por_indicador", {}).get(ind) or pol["estrategia_padrao"]
            reg["estrategia"] = est
            if base is None or est == "suspender":
                reg["valor"], reg["confianca"] = None, 0.0
                conta_conf = "suspenso" if est == "suspender" else "sem dado"
            elif est == "usar_ontem":
                reg["confianca"] = round(max(0.2, 1 - 0.2 * s["atraso"]), 2)
                conta_conf = f"100% − 20 p.p. × {n_(s['atraso'], 'dia')}"
                reg["conta"] += f" (repetido: {n_(s['atraso'], 'dia')} de atraso)"
            else:
                reg["valor"], conta_est = _estimar(ind, base, s["atraso"], mercado, publicados)
                reg["confianca"] = 0.6
                reg["conta"] = "estimado: " + conta_est
                conta_conf = "estimativa"
                origem = "derivado"
                db["estimativas"].append({"indicador": ind, "data": s["esperada"], "valor": reg["valor"],
                                          "feita_em": d.isoformat()})
            chave = f"DEFAS-{ind}"
            if s["atraso"] >= 3:
                estado["alertas"].setdefault(chave, {
                    "titulo": f"Painel: {meta['nome']} defasado", "area": "dashboards", "sev": "media",
                    "aberto_em": d.isoformat(), "corpo": ""})
                estado["alertas"][chave]["corpo"] = (f"O indicador está {s['atraso']} dias úteis atrás. Estratégia "
                                                     f"atual: `{est}`.")
                estado["alertas"][chave]["detalhe"] = f"{s['atraso']} dias úteis de defasagem; estratégia `{est}`"
        else:
            estado["alertas"].pop(f"DEFAS-{ind}", None)
        if ind in ("bova11", "dolar") and base:
            reg["tendencia"] = _tendencia(mercado, base["serie"], base["data"], janela)
        publicados[ind] = reg
        valor_txt = config.formatar(ind, reg["valor"]) if reg["valor"] is not None else "não publicado"
        situ = ("em dia" if s["atraso"] == 0 else f"{n_(s['atraso'], 'dia')} atrás · `{reg['estrategia']}`")
        if s["via"] == "alternativa":
            situ += " · via alternativa"
        linhas.append([meta["nome"], cel(valor_txt, origem if reg["valor"] is not None else "decisao",
                                         "estimado" if reg["estrategia"] == "estimar" else None),
                       data(reg["data_ref"]), data(s["esperada"]), situ, cel(reg["conta"], origem),
                       cel(pct(reg["confianca"], 0), "regra", conta_conf)])

    # conferência de qualidade (dados reais)
    checks = _qualidade(mercado, publicados, situacao)
    for c in checks:
        if not c["ok"] and c["checagem"].count("×"):
            reg = publicados[c["ind"]]
            reg["confianca"] = round(max(0.0, reg["confianca"] - 0.1), 2)
            reg["alerta_qualidade"] = c["resultado"]
    for ind, reg in publicados.items():
        confs.append(reg["confianca"])
        db["indicadores"][ind] = reg
    tend = [(ind, publicados[ind]["tendencia"]) for ind in ("bova11", "dolar") if publicados[ind].get("tendencia")]
    if tend:
        e.tabela("Tendências usadas pelo comitê", ["Indicador", "De", "Até", "Variação"],
                 [[config.INDICADORES[i]["nome"], f"{num(t['v_de'], 4 if i == 'dolar' else 2)} em {dm(t['de'])}",
                   f"{num(t['v_ate'], 4 if i == 'dolar' else 2)} em {dm(t['ate'])}",
                   cel(f"{pct(t['valor'], 2, True)} em {t['n']} pregões", "derivado")] for i, t in tend])
    b_q = None
    if checks:
        b_q = e.tabela("Conferência de qualidade (dados reais)", ["Checagem", "Resultado", "Regra", "Ok?"],
                       [[c["checagem"], cel(c["resultado"], "derivado"), c["regra"], "✓" if c["ok"] else "✗"]
                        for c in checks])

    # estimativas antigas são conferidas quando o dado real chega
    tol = pol.get("tolerancia_erro_estimativa", {})
    pendentes, conferidas = [], []
    for est_ in db["estimativas"]:
        ind = est_["indicador"]
        lib = situacao[ind]["lib"]
        if est_.get("feita_em") == d.isoformat() or lib is None or lib < est_["data"]:
            if est_["data"] >= (d - timedelta(days=20)).isoformat():
                pendentes.append(est_)
            continue
        real = _calc_indicador(ind, mercado, est_["data"], estado, "principal")
        if not real or real["data"] != est_["data"]:
            continue
        relativo = ind in ("dolar", "ibov", "bova11")
        erro = abs(est_["valor"] - real["valor"]) / (abs(real["valor"]) if relativo else 1)
        ok = erro <= tol.get(ind, 0.01)
        conferidas.append([config.INDICADORES[ind]["nome"], data(est_["data"]), cel(num(est_["valor"], 4), "derivado"),
                           cel(num(real["valor"], 4), "real"),
                           pct(erro, 2) if relativo else f"{num(erro, 2)} p.p.",
                           pct(tol.get(ind, 0.01), 1) if relativo else f"{num(tol.get(ind, 0.01), 2)} p.p.",
                           cel("acertou" if ok else "errou", "derivado")])
        if ok:
            estado["metricas"]["estimativas_ok"] += 1
        else:
            estado["metricas"]["estimativas_erro"] += 1
            times_.registrar_erro_estimativa(estado, ind, d)
            estado["alertas"][f"ERRO-{ind}-{est_['data']}"] = {
                "titulo": f"Painel errou {config.INDICADORES[ind]['nome']} de {est_['data']}", "area": "dashboards",
                "sev": "media", "aberto_em": d.isoformat(), "expira": 5,
                "corpo": f"Estimado {est_['valor']}, real {real['valor']}. O comitê decidiu com o número estimado."}
            eventos.append(_evento("dashboards", "alerta", f"Estimativa errada de {ind} em {est_['data']}: "
                                   f"{est_['valor']} vs real {real['valor']}"))
    db["estimativas"] = pendentes
    b_conf = None
    if conferidas:
        b_conf = e.tabela("Estimativas conferidas com o dado real", ["Indicador", "Data", "Estimado", "Real", "Erro",
                          "Tolerância", "Resultado"], conferidas)

    # credibilidade
    media = sum(confs) / len(confs)
    acertos = sum(1 for c in conferidas if c[6]["v"] == "acertou")
    erros = len(conferidas) - acertos
    antes = db["credibilidade"]
    C = CREDIBILIDADE
    depois = antes + C["acerto"] * acertos - C["erro"] * erros
    ajuste = C["sens_confianca"] * (media - C["confianca_alvo"])
    db["credibilidade"] = round(min(1.0, max(0.0, depois + ajuste)), 3)
    db["confianca_media"] = round(media, 3)
    b_cred = e.contas("Credibilidade dos painéis", [
        {"rot": "ontem", "expr": "", "valor": pct(antes, 1), "o": "simulado"},
        {"rot": "estimativas que acertaram", "expr": f"{acertos} × {pp(C['acerto'], 0)}", "valor": pp(C["acerto"] * acertos, 1), "o": "regra"},
        {"rot": "estimativas que erraram", "expr": f"{erros} × −{pp(C['erro'], 0)[1:]}", "valor": pp(-C["erro"] * erros, 1), "o": "regra"},
        {"rot": "confiança média de hoje", "expr": f"{num(C['sens_confianca'], 2)} × ({pct(media, 1)} − {pct(C['confianca_alvo'], 0)})",
         "valor": pp(ajuste, 2), "o": "regra"},
        {"rot": "hoje", "expr": "entre 0% e 100%", "valor": pct(db["credibilidade"], 1), "o": "simulado"},
    ], nota="A credibilidade pesa nas aplicações e resgates dos cotistas e, abaixo de 60%, deixa o comitê na defensiva.")

    if checks:
        ruins = [c for c in checks if not c["ok"]]
        if ruins:
            e.diz(1, "Na conferência: " + "; ".join(f"{c['checagem']}: {c['resultado']} (fora da regra: {c['regra']})"
                                                     for c in ruins) + ".", tipo="alerta", bloco=b_q, minutos=10)
        else:
            maior = max((c for c in checks if "z" in c), key=lambda c: abs(c["z"]), default=None)
            div = [c for c in checks if "z" not in c]
            texto = "Conferência ok: " + "; ".join(f"{c['checagem'].split(' em ')[0]} {c['resultado'].split(' (')[-1].rstrip(')')}"
                                                   for c in div)
            if maior:
                texto += (f"; maior variação do dia {maior['checagem'].split(' em ')[0].replace('variação de ', '')} "
                          f"{pct(maior['var'], 2, True)} ({num(abs(maior['z']), 1)} desvios-padrão)")
            e.diz(1, texto + ".", bloco=b_q, minutos=10)
    if conferidas:
        e.diz(0, "Estimativas conferidas: " + "; ".join(f"{c[0]} de {c[1][:5]}: estimado {c[2]['v']}, real {c[3]['v']} → "
                                                        f"{c[6]['v']}" for c in conferidas) + ".",
              tipo="alerta" if erros else "fala", bloco=b_conf, minutos=14)
    e.diz(0, f"Painel publicado com confiança média {pct(media, 0)}. Credibilidade {pct(antes, 1)} → "
             f"{pct(db['credibilidade'], 1)}.", bloco=b_cred, minutos=16)
    if any(r["valor"] is None for r in publicados.values()) or db["credibilidade"] < 0.6:
        e.status("ruim", f"{em_dia}/{len(situacao)} em dia · credibilidade {pct(db['credibilidade'], 0)}")
    elif atrasados or db["credibilidade"] < 0.8:
        e.status("aviso", f"{em_dia}/{len(situacao)} em dia · credibilidade {pct(db['credibilidade'], 0)}")
    else:
        e.status("ok", f"{em_dia}/{len(situacao)} em dia · credibilidade {pct(db['credibilidade'], 0)}")
    e.dados["bloco_principal"] = b_painel
    if em_dia == len(situacao):
        estado["metricas"]["dias_em_dia"] += 1
    return {"estrategias": {i: r["estrategia"] for i, r in publicados.items() if r["estrategia"]},
            "situacao": situacao}


# ====================================================================== 10h · Comitê
def _pesos(posicoes: dict) -> dict:
    total = sum(p["valor"] for p in posicoes.values())
    return {a: (p["valor"] / total if total else 0.0) for a, p in posicoes.items()}


def _desempenho(fundo: dict, janela: int = 21) -> dict:
    hist = fundo["hist_cota"][-(janela + 1):]
    ret_f = hist[-1][1] / hist[0][1] - 1 if len(hist) > 1 else 0.0
    ret_c = hist[-1][2] / hist[0][2] - 1 if len(hist) > 1 else 0.0
    return {"ret_fundo": ret_f, "ret_cdi": ret_c, "excesso": ret_f - ret_c, "janela": len(hist) - 1,
            "desde": hist[0][0]}


def _etapa_comite(rastro: Rastro, estado: dict, d: date, politicas: dict, intervencao: dict, eventos: list) -> dict:
    e = rastro.etapa("comite", "executivos", "10:00", "Comitê", "Mexemos na carteira, na equipe ou no orçamento?")
    fundo, exe = estado["fundo"], estado["executivos"]
    indicadores = estado["dashboards"]["indicadores"]
    max_def = politicas["executivos"]["max_defasagem_para_operar"]
    congelados = set()
    for ind, meta in config.INDICADORES.items():
        reg = indicadores.get(ind, {})
        if meta["ativo"] and meta["ativo"] != "caixa" and (reg.get("valor") is None or reg.get("defasagem", 0) > max_def):
            congelados.add(meta["ativo"])
    des = _desempenho(fundo)
    ctx = {"congelados": sorted(congelados), "cota_ontem": fundo["cota"],
           "fluxo_ontem_pct": (fundo["fluxo_dia"] / fundo["pl"]) if fundo["pl"] else 0.0, **des}
    ctx["defensivo"] = estado["dashboards"]["credibilidade"] < 0.6 or des["excesso"] < -0.01
    alvo_antes = dict(exe["alvo"])
    reunioes_antes = estado["times"]["comite"]["ultimo"] if estado.get("times") else None
    dex = times_.comite(e, estado, d, politicas, ctx, intervencao)
    if estado["times"]["comite"]["ultimo"] != reunioes_antes:
        estado["metricas"]["reunioes"] += 1
    if dex.get("alocacao"):
        exe["alvo"] = dict(dex["alocacao"])
        if any(abs(exe["alvo"][a] - alvo_antes[a]) > 1e-9 for a in alvo_antes):
            estado["metricas"]["mudancas_alvo"] += 1
    if "equipe_extracao" in dex:
        estado["extracao"]["equipe"] = int(dex["equipe_extracao"])
    if "orcamento_extracao_dia" in dex:
        estado["extracao"]["orcamento_dia"] = float(dex["orcamento_extracao_dia"])
    exe["congelados"] = sorted(congelados)
    if dex:
        exe["ultima_decisao"] = d.isoformat()
        autor = "conselho" if intervencao.get("executivos") else "comitê"
        exe["decisoes_recentes"] = (exe["decisoes_recentes"] + [{"data": d.isoformat(), "autor": autor,
                                    "resumo": dex.get("justificativa", "")[:300],
                                    "alvo_antes": alvo_antes, "alvo": dict(exe["alvo"])}])[-20:]
    exe["dias_sem_decisao"] = 0
    if dex.get("alocacao") and exe["alvo"] != alvo_antes:
        e.status("aviso" if ctx["defensivo"] else "ok", "novo alvo: " + ", ".join(
            f"{config.ATIVOS[a].split(' (')[0]} {pct(w, 1)}" for a, w in exe["alvo"].items()))
    elif congelados:
        e.status("aviso", "congelados: " + ", ".join(sorted(congelados)))
    else:
        e.status("ok", "alvo mantido" + (" · equipe/orçamento ajustados" if dex else ""))
    return dex | {"_ctx": ctx, "_alvo_antes": alvo_antes}


# ====================================================================== 18h · Fundo
def _etapa_fundo(rastro: Rastro, estado: dict, d: date, anterior: date, mercado: Mercado, politicas: dict,
                 dex: dict, eventos: list) -> dict:
    e = rastro.etapa("fundo", "fundo", "18:00", "Fundo", "Quanto o fundo ganhou ou perdeu, e por quê?")
    fundo, exe, ref = estado["fundo"], estado["executivos"], estado["referencia"]
    pf = politicas["fundo"]
    pl_ini = sum(p["valor"] for p in fundo["posicoes"].values())
    cotas_ini, cota_ant = fundo["cotas"], fundo["cota"]

    # 1) marcação a mercado com os preços oficiais do dia
    fator_cdi, dias_cdi = _fator_cdi(mercado, anterior, d)
    linhas, pnl = [], {}
    retornos = {}
    for ativo, pos in fundo["posicoes"].items():
        antes = pos["valor"]
        if ativo == "caixa":
            pos["valor"] *= fator_cdi
            pnl[ativo] = pos["valor"] - antes
            retornos[ativo] = fator_cdi - 1
            linhas.append([config.ATIVOS[ativo], "CDI", "—",
                           cel(" × ".join(f"(1 + {num(t, 6)}%)" for _, t, _ in dias_cdi), "real",
                               "; ".join(f"CDI de {dm(dd)}" for dd, _, _ in dias_cdi)),
                           cel(pct(fator_cdi - 1, 4, True), "derivado"), mi(antes, 2), cel(mil(pnl[ativo]), "derivado")])
            continue
        c = cotacao(mercado, ativo, d, pos.get("titulo"))
        if c is None:
            pnl[ativo], retornos[ativo] = 0.0, 0.0
            linhas.append([config.ATIVOS[ativo], "—", "—", "sem preço", "—", mi(antes, 2), "R$ 0"])
            continue
        casas = 4 if ativo == "dolar" else 2
        if pos.get("titulo") and c["titulo"] != pos["titulo"]:
            eventos.append(_evento("fundo", "info", f"{config.ATIVOS[ativo]}: troca de título {pos['titulo']} → {c['titulo']}"))
            linhas.append([config.ATIVOS[ativo], c["rotulo"], f"título {pos['titulo'][:4]} venceu/saiu",
                           cel(f"{num(c['preco'], casas)} ({dm(c['data'])}, {c['fonte']})", "real"),
                           "rolagem: mesmo valor", mi(antes, 2), "R$ 0"])
            pos.update(preco=c["preco"], titulo=c["titulo"], data_preco=c["data"], serie=c["serie"])
            ref["posicoes"][ativo].update(preco=c["preco"], titulo=c["titulo"], data_preco=c["data"], serie=c["serie"])
            pnl[ativo], retornos[ativo] = 0.0, 0.0
            continue
        ret = c["preco"] / pos["preco"] - 1 if pos.get("preco") else 0.0
        pos["valor"] *= 1 + ret
        pnl[ativo], retornos[ativo] = pos["valor"] - antes, ret
        linhas.append([config.ATIVOS[ativo], c["rotulo"],
                       cel(f"{num(pos['preco'], casas)} ({dm(pos.get('data_preco'))})", "real"),
                       cel(f"{num(c['preco'], casas)} ({dm(c['data'])}, {c['fonte']})", "real"),
                       cel(pct(ret, 2, True), "derivado"), mi(antes, 2), cel(mil(pnl[ativo]), "derivado")])
        pos.update(preco=c["preco"], titulo=c["titulo"], data_preco=c["data"], serie=c["serie"])
    b_precos = e.tabela(f"Marcação a mercado de {data(d.isoformat())}", ["Ativo", "Instrumento", "Preço anterior",
                        "Preço de hoje", "Variação", "Valor antes", "Resultado"], linhas,
                        nota="Preços oficiais do administrador: não dependem do portão da Extração (o fundo é "
                             "marcado pelo mercado mesmo quando a gestora está sem o dado).")
    fundo["bench"] *= fator_cdi

    # 2) taxa de administração
    pl_bruto = sum(p["valor"] for p in fundo["posicoes"].values())
    n_dias = len(calendario.dias_uteis_entre(anterior, d)) or 1
    taxa = pl_bruto * pf["taxa_adm"] / 252 * n_dias
    fundo["posicoes"]["caixa"]["valor"] -= taxa
    pl = pl_bruto - taxa
    cota_pre = pl / fundo["cotas"]
    fundo["hist_cota"].append([d.isoformat(), cota_pre, fundo["bench"]])
    del fundo["hist_cota"][:-60]

    # 3) cotistas: modelo sem sorteio
    cm = _cotistas(politicas)
    des = _desempenho(fundo, cm["janela"])
    cred = estado["dashboards"]["credibilidade"]
    termo_d = cm["sens_desempenho"] * des["excesso"]
    termo_c = cm["sens_credibilidade"] * (cred - cm["credibilidade_neutra"])
    bruto = cm["captacao_base"] + termo_d + termo_c
    fluxo_pct = max(-cm["limite"], min(cm["limite"], bruto))
    fluxo = pl * fluxo_pct
    fundo["posicoes"]["caixa"]["valor"] += fluxo
    fundo["cotas"] += fluxo / cota_pre
    fundo["fluxo_dia"] = round(fluxo, 2)
    b_fluxo = e.contas("Aplicações e resgates dos cotistas (modelo, sem sorteio)", [
        {"rot": "captação de base", "expr": "", "valor": pct(cm["captacao_base"], 3, True), "o": "regra"},
        {"rot": "desempenho", "expr": f"{num(cm['sens_desempenho'], 2)} × excesso sobre o CDI em {des['janela']} pregões "
                                      f"({pp(des['excesso'], 2)})", "valor": pct(termo_d, 3, True), "o": "derivado"},
        {"rot": "credibilidade", "expr": f"{num(cm['sens_credibilidade'], 3)} × ({pct(cred, 1)} − {pct(cm['credibilidade_neutra'], 0)})",
         "valor": pct(termo_c, 3, True), "o": "simulado"},
        {"rot": "fluxo do dia", "expr": f"soma, limitada a ±{pct(cm['limite'], 0)} · × patrimônio {mi(pl)}",
         "valor": f"{pct(fluxo_pct, 3, True)} = {mil(fluxo)}", "o": "simulado"},
    ], nota="Cotista aplica quando o fundo bate o CDI e confia nos números; resgata quando perde. Aplicação entra "
            "no caixa e compra cotas pelo valor do dia: não muda a cota.")
    if fluxo_pct < -0.01:
        estado["alertas"][f"RESGATE-{d}"] = {
            "titulo": f"Resgate relevante em {d}: {fluxo_pct:.2%} do PL", "area": "executivos", "sev": "alta",
            "aberto_em": d.isoformat(), "expira": 5,
            "corpo": f"Saíram {brl(-fluxo)}. Excesso sobre o CDI: {pp(des['excesso'], 2)}; credibilidade {pct(cred, 0)}."}

    # 4) rebalanceamento para o alvo (ativo congelado fica onde está)
    congelados = set(exe.get("congelados", []))
    pesos = _pesos(fundo["posicoes"])
    alvo = dict(exe["alvo"])
    if congelados:
        livre = 1 - sum(pesos[a] for a in congelados)
        base = sum(alvo[a] for a in alvo if a not in congelados)
        alvo = {a: (pesos[a] if a in congelados else (alvo[a] / base * livre if base else 0)) for a in alvo}
    desvio = max(abs(pesos[a] - alvo[a]) for a in alvo)
    tol = politicas["executivos"]["rebalancear_se_desvio_maior_que"]
    alvo_mudou = bool(dex.get("alocacao")) and dex["alocacao"] != dex.get("_alvo_antes")
    motivo = ("o comitê mudou o alvo hoje" if alvo_mudou else
              f"desvio de {pp(desvio, 1)[1:]} passou da tolerância de {pp(tol, 0)[1:]}" if desvio > tol else
              "caixa negativo" if fundo["posicoes"]["caixa"]["valor"] < 0 else None)
    giro = custo = 0.0
    b_reb = None
    if motivo:
        total = sum(p["valor"] for p in fundo["posicoes"].values())
        giro = sum(abs(alvo[a] * total - fundo["posicoes"][a]["valor"]) for a in alvo) / 2
        custo = giro * pf["custo_transacao"]
        total -= custo
        linhas = []
        for a in alvo:
            antes = fundo["posicoes"][a]["valor"]
            fundo["posicoes"][a]["valor"] = alvo[a] * total
            delta = fundo["posicoes"][a]["valor"] - antes
            linhas.append([config.ATIVOS[a], f"{mi(antes, 2)} ({pct(antes / (total + custo), 1)})",
                           pct(alvo[a], 1) + (" (congelado)" if a in congelados else ""),
                           cel(("compra " if delta > 0 else "venda ") + mi(abs(delta), 2) if abs(delta) > 1 else "—", "decisao")])
        b_reb = e.tabela("Rebalanceamento", ["Ativo", "Antes", "Alvo", "Operação"], linhas,
                         nota=f"Motivo: {motivo}. Giro {mi(giro, 2)} × custo de {pct(pf['custo_transacao'], 2)} = {brl(custo)}.")
        if giro > 0:
            eventos.append(_evento("fundo", "info", f"Rebalanceamento: giro {mi(giro, 1)}, custo {brl(custo)}"))
        estado["metricas"]["giro"] += giro
        estado["metricas"]["custo_giro"] += custo

    # 5) fechamento
    fundo["pl"] = round(sum(p["valor"] for p in fundo["posicoes"].values()), 2)
    fundo["cota"] = fundo["pl"] / fundo["cotas"]
    fundo["retorno_dia"] = fundo["cota"] / cota_ant - 1
    fundo["hist_cota"][-1][1] = fundo["cota"]
    resultado = sum(pnl.values())
    linhas = [[config.ATIVOS[a], cel(mil(v), "derivado"), cel(pp(v / pl_ini, 3) if pl_ini else "—", "derivado")]
              for a, v in pnl.items()]
    linhas += [["Taxa de administração", cel(mil(-taxa), "regra"), cel(pp(-taxa / pl_ini, 3), "regra")],
               ["Custo de transação", cel(mil(-custo), "regra"), cel(pp(-custo / pl_ini, 3), "regra")]]
    b_atrib = e.tabela("De onde veio o resultado do dia", ["Componente", "Resultado", "Contribuição na cota"], linhas,
                       nota=f"Retorno da cota = soma das contribuições = {pct(fundo['retorno_dia'], 3, True)}.")
    conferencia = pl_ini + resultado - taxa - custo + fluxo
    b_conta = e.contas("Patrimônio: a conta fecha", [
        {"rot": "patrimônio de ontem", "expr": "", "valor": brl(pl_ini, 2), "o": "simulado"},
        {"rot": "resultado dos ativos", "expr": "marcação + CDI", "valor": brl(resultado, 2), "o": "derivado"},
        {"rot": "taxa de administração", "expr": f"{mi(pl_bruto, 2)} × {pct(pf['taxa_adm'], 0)} ÷ 252 × {n_dias}",
         "valor": brl(-taxa, 2), "o": "regra"},
        {"rot": "custo de transação", "expr": f"giro {mi(giro, 2)} × {pct(pf['custo_transacao'], 2)}", "valor": brl(-custo, 2), "o": "regra"},
        {"rot": "aplicações − resgates", "expr": "", "valor": brl(fluxo, 2), "o": "simulado"},
        {"rot": "patrimônio de hoje", "expr": "soma das posições", "valor": brl(fundo["pl"], 2), "o": "simulado"},
        {"rot": "cota", "expr": f"{brl(fundo['pl'], 2)} ÷ {num(fundo['cotas'], 2)} cotas", "valor": num(fundo["cota"], 6), "o": "simulado"},
    ])

    # 6) carteira de referência: nunca muda de ideia (alocação neutra, rebalanceada por desvio)
    neutro = pf["alocacao_inicial"]
    ref_ini = sum(p["valor"] for p in ref["posicoes"].values())
    for a, p in ref["posicoes"].items():
        p["valor"] *= 1 + retornos[a]
        if a != "caixa":
            pos = fundo["posicoes"][a]
            p.update(preco=pos["preco"], titulo=pos["titulo"], data_preco=pos["data_preco"], serie=pos["serie"])
    ref_bruto = sum(p["valor"] for p in ref["posicoes"].values())
    ref_taxa = ref_bruto * pf["taxa_adm"] / 252 * n_dias
    ref["posicoes"]["caixa"]["valor"] -= ref_taxa
    pesos_ref = _pesos(ref["posicoes"])
    ref_reb = ""
    if max(abs(pesos_ref[a] - neutro[a]) for a in neutro) > tol:
        tot = sum(p["valor"] for p in ref["posicoes"].values())
        g = sum(abs(neutro[a] * tot - ref["posicoes"][a]["valor"]) for a in neutro) / 2
        tot -= g * pf["custo_transacao"]
        for a in neutro:
            ref["posicoes"][a]["valor"] = neutro[a] * tot
        ref_reb = f" Rebalanceou para o neutro (giro {mi(g, 1)})."
    ref_pl = sum(p["valor"] for p in ref["posicoes"].values())
    cota_ref_ant = ref["cota"]
    ref["cota"] = ref_pl / ref["cotas"]
    valor_decisoes = fundo["cota"] / ref["cota"] - 1
    b_ref = e.contas("Carteira de referência (o fundo sem o comitê)", [
        {"rot": "cota de ontem", "expr": "", "valor": num(cota_ref_ant, 6), "o": "simulado"},
        {"rot": "mesmos preços de hoje", "expr": "alocação neutra " + ", ".join(f"{config.ATIVOS[a].split(' (')[0]} {pct(w, 0)}"
                                                                               for a, w in neutro.items()),
         "valor": pct(ref_pl / ref_ini - 1, 3, True), "o": "derivado"},
        {"rot": "cota de hoje", "expr": "mesma taxa de administração, sem cotistas" + ref_reb, "valor": num(ref["cota"], 6), "o": "simulado"},
        {"rot": "valor das decisões até hoje", "expr": f"cota do fundo {num(fundo['cota'], 6)} ÷ referência {num(ref['cota'], 6)} − 1",
         "valor": pct(valor_decisoes, 2, True), "o": "derivado"},
    ], nota="Se o comitê não acrescenta nada, fundo e referência andam juntos. A diferença é o valor (ou o custo) das decisões.")

    # enquadramento
    pesos = _pesos(fundo["posicoes"])
    for ativo, (mn, mx) in pf["limites"].items():
        chave = f"DESENQ-{ativo}"
        if pesos[ativo] < mn - 1e-6 or pesos[ativo] > mx + 1e-6:
            estado["alertas"].setdefault(chave, {"titulo": f"Desenquadramento: {config.ATIVOS[ativo]}", "area": "executivos",
                                                 "sev": "alta", "aberto_em": d.isoformat(), "corpo": ""})
            estado["alertas"][chave]["corpo"] = f"Peso {pct(pesos[ativo], 1)} fora do limite {pct(mn, 0)}–{pct(mx, 0)}."
        else:
            estado["alertas"].pop(chave, None)

    # falas do administrador
    precos = [ln for ln in b_linhas(e, b_precos) if ln[0] != config.ATIVOS["caixa"] and isinstance(ln[4], dict)]
    e.diz(0, "Preços oficiais de hoje: " + "; ".join(f"{ln[1]} {ln[3]['v'].split(' (')[0]} ({ln[4]['v']})" for ln in precos)
          + f". O caixa rendeu o CDI ({pct(fator_cdi - 1, 4, True)}).", bloco=b_precos, minutos=0)
    principais = sorted(pnl.items(), key=lambda kv: -abs(kv[1]))[:2]
    e.diz(0, f"Resultado dos ativos: {mil(resultado, True)} ({pct(resultado / pl_ini, 2, True)}), puxado por "
          + " e ".join(f"{config.ATIVOS[a]} ({mil(v, True)})" for a, v in principais)
          + f". Taxa de administração {mil(taxa)}.", bloco=b_atrib, minutos=4)
    e.diz(0, f"Cotistas: excesso de {pp(des['excesso'], 2)} sobre o CDI em {n_(des['janela'], 'pregão', 'pregões')} e credibilidade "
             f"{pct(cred, 0)} → fluxo de {pct(fluxo_pct, 3, True)} do patrimônio = {mil(fluxo)} "
             f"({'aplicações' if fluxo >= 0 else 'resgates'}).", bloco=b_fluxo, minutos=6)
    if b_reb:
        compras = [f"{ln[3]['v']} de {ln[0]}" for ln in b_linhas(e, b_reb) if isinstance(ln[3], dict) and ln[3]["v"] != "—"]
        e.diz(0, f"Rebalanceamento ({motivo}): " + "; ".join(compras) + f". Custo {brl(custo)}.", bloco=b_reb,
              tipo="evento", minutos=8)
    e.diz(0, f"Cota {num(fundo['cota'], 6)} ({pct(fundo['retorno_dia'], 2, True)}), patrimônio {mi(fundo['pl'])}. "
             f"Carteira de referência {num(ref['cota'], 6)}: as decisões somam {pct(valor_decisoes, 2, True)} até aqui.",
          bloco=b_conta, minutos=10)
    desenq = [k for k in estado["alertas"] if k.startswith("DESENQ-")]
    nivel = "ruim" if fluxo_pct < -0.01 or desenq else "ok"  # dia negativo é mercado, não problema do processo
    e.status(nivel, f"cota {num(fundo['cota'], 6)} ({pct(fundo['retorno_dia'], 2, True)}) · PL {mi(fundo['pl'])}")
    e.dados["bloco_principal"] = b_atrib
    estado["metricas"]["taxa"] += taxa
    estado["metricas"]["fluxo"] += fluxo
    return {"pl_ini": pl_ini, "resultado": resultado, "taxa": taxa, "custo": custo, "fluxo": fluxo,
            "pl_fim": fundo["pl"], "n_dias": n_dias, "conferencia": conferencia, "valor_decisoes": valor_decisoes,
            "cotas_ini": cotas_ini}


def b_linhas(etapa, bloco_id: str) -> list:
    return next(b for b in etapa.dados["blocos"] if b["id"] == bloco_id)["linhas"]


# ====================================================================== 18h30 · Empresa
def _etapa_empresa(rastro: Rastro, estado: dict, d: date, politicas: dict, conta_fundo: dict) -> dict:
    e = rastro.etapa("empresa", "executivos", "18:30", "Empresa", "A gestora se paga?")
    g, ex, pg = estado["gestora"], estado["extracao"], politicas["gestora"]
    n = conta_fundo["n_dias"]
    caixa_ant = g["caixa"]
    receita = conta_fundo["taxa"]
    custo_eq = ex["equipe"] * pg["custo_engenheiro_dia"] * n
    custo = (pg["custo_fixo_dia"] * n) + custo_eq + ex["orcamento_dia"] * n
    g["receita_dia"], g["custo_dia"] = round(receita, 2), round(custo, 2)
    g["caixa"] = round(caixa_ant + receita - custo, 2)
    folego = g["caixa"] / (custo / n) if custo else 999
    b = e.contas("Resultado da gestora no dia", [
        {"rot": "caixa de ontem", "expr": "", "valor": brl(caixa_ant, 2), "o": "simulado"},
        {"rot": "receita: taxa de administração", "expr": "1% a.a. do patrimônio do fundo, cobrado por dia útil",
         "valor": brl(receita, 2), "o": "derivado"},
        {"rot": "custo fixo da casa", "expr": f"{brl(pg['custo_fixo_dia'])} × {n}", "valor": brl(-pg["custo_fixo_dia"] * n, 2), "o": "regra"},
        {"rot": "equipe de Extração", "expr": f"{ex['equipe']} × {brl(pg['custo_engenheiro_dia'])} × {n}", "valor": brl(-custo_eq, 2), "o": "decisao"},
        {"rot": "orçamento de Extração", "expr": f"{brl(ex['orcamento_dia'])} × {n}", "valor": brl(-ex["orcamento_dia"] * n, 2), "o": "decisao"},
        {"rot": "caixa de hoje", "expr": f"fôlego de {num(folego, 0)} dias de custo", "valor": brl(g["caixa"], 2), "o": "simulado"},
    ])
    if g["caixa"] < 0:
        estado["alertas"].setdefault("CRISE-CAIXA", {
            "titulo": "Caixa da gestora negativo", "area": "executivos", "sev": "alta", "aberto_em": d.isoformat(),
            "corpo": "A receita de taxa não cobre os custos. Reduzir equipe/orçamento ou recuperar patrimônio."})
    else:
        estado["alertas"].pop("CRISE-CAIXA", None)
    e.diz(0, f"Receita de taxa hoje {brl(receita)} contra custos de {brl(custo)} (casa {brl(pg['custo_fixo_dia'] * n)} + "
             f"{n_(ex['equipe'], 'engenheiro')} {brl(custo_eq)} + orçamento {brl(ex['orcamento_dia'] * n)}): "
             f"{'sobra' if receita >= custo else 'falta'} {brl(abs(receita - custo))}. Caixa da gestora {brl(g['caixa'])} "
             f"({num(folego, 0)} dias de fôlego).", bloco=b)
    nivel = "ruim" if g["caixa"] < 0 else "aviso" if receita < custo else "ok"
    e.status(nivel, f"{'sobra' if receita >= custo else 'falta'} {brl(abs(receita - custo))} no dia · caixa {brl(g['caixa'])}")
    e.dados["bloco_principal"] = b
    return {"caixa_ant": caixa_ant, "receita": receita, "custo": custo}


# ====================================================================== alertas e eventos
def _evento(area: str, tipo: str, texto: str, chave: str | None = None) -> dict:
    return {"area": area, "tipo": tipo, "texto": texto, "chave": chave}


def _alertas_de_incidentes(estado: dict, d: date) -> None:
    for inc in estado["incidentes"]:
        chave = inc["id"]
        if inc["estado"] == "aberto":
            fonte = config.FONTES[inc["fonte"]]["nome"]
            sev = "alta" if inc["tipo"] in ("falha_real", "mudanca_formato") or inc["dias"] >= 3 else "media"
            origem = "falha REAL" if inc["tipo"] == "falha_real" else "teste de estresse (falha simulada)"
            estado["alertas"][chave] = {
                "titulo": f"{chave} · {fonte}: {config.TIPOS_INCIDENTE[inc['tipo']]}", "area": "extracao", "sev": sev,
                "aberto_em": inc["aberto_em"],
                "corpo": (f"**Fonte:** {fonte}\n**Origem:** {origem}\n**Tipo:** `{inc['tipo']}` — {inc['detalhe']}\n"
                          f"**Ação atual:** `{inc['acao']}` · **dias aberto:** {inc['dias']}\n\n"
                          f"Ações possíveis: " + ", ".join(f"`{a}`" for a in config.ACOES_EXTRACAO)),
                "detalhe": f"dia {inc['dias']}, ação `{inc['acao']}`",
            }
        else:
            estado["alertas"].pop(chave, None)
    for chave in [k for k, a in estado["alertas"].items() if a.get("expira")]:
        a = estado["alertas"][chave]
        if len(calendario.dias_uteis_entre(date.fromisoformat(a["aberto_em"]), d)) >= a["expira"]:
            del estado["alertas"][chave]


# ====================================================================== o dia
def simular_dia(estado: dict, d: date, mercado: Mercado, politicas: dict, decisao: dict | None,
                controle: dict | None = None, modo: str = "diario") -> tuple[dict, dict]:
    """Avança a empresa até o fechamento do dia útil `d`. Devolve (novo_estado, registro_do_dia).

    Os times decidem tudo. `decisao` é a diretriz opcional do conselho: o que estiver nela vale por cima do time."""
    estado = copy.deepcopy(estado)
    anterior = date.fromisoformat(estado["ultima_data"])
    if d <= anterior:
        raise ValueError(f"{d} já foi simulado (último: {anterior})")
    intervencao = decisao or {}
    eventos: list[dict] = []
    alertas_antes = set(estado["alertas"])
    rastro = Rastro()
    numero = len(calendario.dias_uteis_entre(date.fromisoformat(estado["inicio"]), d))
    times_.memoria(estado)

    _etapa_heranca(rastro, estado, d, anterior, numero)
    r_ex = _etapa_extracao(rastro, estado, d, mercado, controle, politicas, intervencao, eventos, modo)
    r_db = _etapa_dashboards(rastro, estado, d, mercado, politicas, intervencao, eventos)
    dex = _etapa_comite(rastro, estado, d, politicas, intervencao, eventos)
    ctx_comite = dex.pop("_ctx")
    alvo_antes = dex.pop("_alvo_antes")
    conta_fundo = _etapa_fundo(rastro, estado, d, anterior, mercado, politicas, dex | {"_alvo_antes": alvo_antes}, eventos)
    conta_empresa = _etapa_empresa(rastro, estado, d, politicas, conta_fundo)
    _alertas_de_incidentes(estado, d)
    estado["ultima_data"] = d.isoformat()
    checks = verificacoes.verificar(rastro, estado, d, mercado, politicas, conta_fundo, conta_empresa, r_db["situacao"])
    m = estado["metricas"]
    m["dias"] += 1
    ok = sum(c["ok"] for c in checks)
    m["verificacoes_ok"] += ok
    m["verificacoes_falha"] += len(checks) - ok
    m["falhas"] = (m["falhas"] + [{"data": d.isoformat(), "id": c["id"], "detalhe": c["detalhe"]}
                                  for c in checks if not c["ok"]])[-20:]
    estado["versao"] = VERSAO_MOTOR

    abertos = set(estado["alertas"]) - alertas_antes
    fechados = alertas_antes - set(estado["alertas"])
    fundo = estado["fundo"]
    autor = "conselho + times" if intervencao else "times"
    registro = {
        "data": d.isoformat(),
        "versao_motor": VERSAO_MOTOR,
        "dia_numero": numero,
        "decisao": {"existe": True, "autor": autor, "intervencao": bool(intervencao)},
        "decisoes": {"extracao": r_ex["acoes"], "dashboards": r_db["estrategias"], "executivos": dex},
        "ata": rastro.ata(),
        "rastro": rastro.json(),
        "verificacoes": checks,
        "eventos": eventos,
        "incidentes_do_dia": [{"id": i["id"], "fonte": i["fonte"], "tipo": i["tipo"]}
                              for i in estado["incidentes"] if i["estado"] == "aberto"],
        "alertas_abertos": sorted(abertos),
        "alertas_fechados": sorted(fechados),
        "resumo": {
            "cota": round(fundo["cota"], 8), "pl": fundo["pl"], "bench": round(fundo["bench"], 8),
            "cota_ref": round(estado["referencia"]["cota"], 8),
            "retorno_dia": round(fundo["retorno_dia"], 6), "fluxo": fundo["fluxo_dia"],
            "pesos": {a: round(w, 4) for a, w in _pesos(fundo["posicoes"]).items()},
            "alvo": dict(estado["executivos"]["alvo"]),
            "divida_tecnica": estado["extracao"]["divida_tecnica"],
            "incidentes_abertos": sum(i["estado"] == "aberto" for i in estado["incidentes"]),
            "credibilidade": estado["dashboards"]["credibilidade"],
            "confianca_media": estado["dashboards"]["confianca_media"],
            "caixa_gestora": estado["gestora"]["caixa"],
            "equipe": estado["extracao"]["equipe"], "orcamento_dia": estado["extracao"]["orcamento_dia"],
            "verificacoes_ok": ok, "verificacoes_total": len(checks),
            "status": {et["id"]: et["status"] for et in rastro.json()},
            "excesso_21d": ctx_comite["excesso"],
        },
    }
    return estado, registro
