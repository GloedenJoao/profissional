"""O dia útil da empresa: Extração → Dashboards → Executivos → Fundo → Gestora.

Tudo é determinístico: dado o estado de ontem, os dados reais, as políticas e a decisão do dia,
o resultado é sempre o mesmo (o acaso usa semente derivada da data).
"""
from __future__ import annotations

import copy
import math
import random
from datetime import date, timedelta

from . import calendario, config, times as times_
from .mercado import Mercado

AREAS = {"extracao": "Extração", "dashboards": "Dashboards", "executivos": "Executivos", "fundo": "Fundo"}


def rng(d: date, *nomes: str) -> random.Random:
    prefixo = [config.SEMENTE] if config.SEMENTE else []  # o ao vivo mantém as sementes de sempre
    return random.Random(":".join([*prefixo, d.isoformat(), *nomes]))


# ====================================================================== estado inicial
def estado_inicial(inicio: date, politicas: dict, mercado: Mercado) -> dict:
    g, f = politicas["gestora"], politicas["fundo"]
    estado = {
        "versao": 1,
        "inicio": inicio.isoformat(),
        "ultima_data": inicio.isoformat(),
        "seq_incidente": 0,
        "extracao": {
            "divida_tecnica": 35.0,
            "equipe": g["equipe_extracao_inicial"],
            "orcamento_dia": g["orcamento_extracao_dia_inicial"],
            "fontes": {fo: {"liberado_ate": {}, "alternativa_ligada": False} for fo in config.FONTES},
        },
        "incidentes": [],
        "alertas": {},
        "dashboards": {"credibilidade": 0.85, "indicadores": {}, "estimativas": []},
        "executivos": {"alvo": dict(f["alocacao_inicial"]), "ultima_decisao": None, "dias_sem_decisao": 0,
                       "decisoes_recentes": []},
        "fundo": {"cota": 1.0, "cotas": float(f["pl_inicial"]), "pl": float(f["pl_inicial"]), "bench": 1.0,
                  "posicoes": {}, "fluxo_dia": 0.0},
        "gestora": {"caixa": float(g["caixa_inicial"]), "receita_dia": 0.0, "custo_dia": 0.0},
    }
    for fonte in config.FONTES:
        for serie in config.FONTES[fonte]["series"]:
            estado["extracao"]["fontes"][fonte]["liberado_ate"][serie] = _ultima_ate(mercado, serie, inicio)
    for ativo, w in f["alocacao_inicial"].items():
        valor = f["pl_inicial"] * w
        preco, titulo = _preco_ativo(mercado, ativo, inicio, None)
        estado["fundo"]["posicoes"][ativo] = {"valor": valor, "preco": preco, "titulo": titulo}
    return estado


def _ultima_ate(mercado: Mercado, serie: str, d: date) -> str | None:
    if serie == "tesouro":
        datas = [h for h in (mercado.titulo(t, v, d) for (t, v) in mercado.tesouro()) if h]
        return max((h[0] for h in datas), default=None)
    u = mercado.ultimo(serie, d)
    return u[0] if u else None


# ====================================================================== preços (administrador)
def _preco_ativo(mercado: Mercado, ativo: str, d: date, titulo: str | None) -> tuple[float | None, str | None]:
    """Preço real de marcação. O administrador do fundo tem acesso aos dados mesmo quando a
    Extração da gestora está com problema."""
    if ativo == "caixa":
        return 1.0, None
    if ativo in config.TITULOS:
        tipo, anos = config.TITULOS[ativo]
        if titulo is None or titulo <= d.isoformat() or not mercado.titulo(tipo, titulo, d):
            titulo = mercado.escolher_titulo(tipo, anos, d)
        h = mercado.titulo(tipo, titulo, d) if titulo else None
        return (h[2] if h else None), titulo
    serie, alt = {"dolar": ("dolar", "dolar_ptax"), "bolsa": ("bova11", "bova11_b3")}[ativo]
    u, a = mercado.ultimo(serie, d), mercado.ultimo(alt, d)
    escolhido = max([x for x in (u, a) if x], key=lambda x: x[0], default=None)
    if u and escolhido and escolhido[0] == u[0]:
        escolhido = u
    return (escolhido[1] if escolhido else None), None


def _fator_cdi(mercado: Mercado, inicio: date, fim: date) -> float:
    fator = 1.0
    for d in calendario.dias_uteis_entre(inicio, fim):
        u = mercado.ultimo("cdi", d)
        fator *= 1 + (u[1] if u else 0.05) / 100
    return fator


# ====================================================================== extração
def _data_esperada(serie: str, fonte: str, d: date) -> date:
    if serie == "ipca":
        mes = d.month - 2
        return date(d.year + (mes <= 0) * -1, (mes - 1) % 12 + 1, 1)
    esperada = d
    for _ in range(config.FONTES[fonte]["defasagem"]):
        esperada = calendario.dia_util_anterior(esperada)
    return esperada


def _fonte_real_ok(mercado: Mercado, fonte: str, d: date, controle: dict | None) -> tuple[bool, str]:
    if controle and controle["fontes"].get(fonte, {}).get("status") == "erro":
        return False, controle["fontes"][fonte]["erro"]
    for serie in config.FONTES[fonte]["series"]:
        ultima = _ultima_ate(mercado, serie, d)
        esperada = _data_esperada(serie, fonte, d)
        if ultima is None or ultima < esperada.isoformat():
            return False, f"série {serie} parada em {ultima} (esperado {esperada})"
    return True, ""


def _novo_incidente(estado: dict, fonte: str, tipo: str, d: date, detalhe: str) -> dict:
    estado["seq_incidente"] += 1
    inc = {"id": f"INC-{estado['seq_incidente']:04d}", "fonte": fonte, "tipo": tipo, "aberto_em": d.isoformat(),
           "estado": "aberto", "dias": 0, "esforco": 0, "acao": None, "detalhe": detalhe,
           "resolvido_em": None, "historico": []}
    estado["incidentes"].append(inc)
    return inc


PROB_RESOLVER = {
    # (tipo, ação) -> probabilidade diária de resolver
    ("atraso", "aguardar"): 0.6, ("atraso", "corrigir_conector"): 0.9,
    ("fora_do_ar", "aguardar"): 0.25, ("fora_do_ar", "corrigir_conector"): 0.45,
    ("mudanca_formato", "aguardar"): 0.0,
}


def _passo_extracao(estado: dict, d: date, mercado: Mercado, controle: dict | None, politicas: dict,
                    decisao: dict, eventos: list) -> None:
    ex = estado["extracao"]
    acoes_dec = (decisao.get("extracao") or {}).get("acoes", {})
    padrao = politicas["extracao"]["acao_padrao"]
    real = {f: _fonte_real_ok(mercado, f, d, controle) for f in config.FONTES}

    # 1) ações escolhidas para os incidentes abertos, dentro da capacidade da equipe
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    capacidade = ex["equipe"]
    for inc in sorted(abertos, key=lambda i: (i["tipo"] != "falha_real", i["aberto_em"])):
        acao = acoes_dec.get(inc["id"]) or inc.get("acao_escolhida") or padrao.get(inc["tipo"], "aguardar")
        if inc["id"] in acoes_dec:
            inc["acao_escolhida"] = acoes_dec[inc["id"]]
        custo = config.CUSTO_ACAO[acao]
        if custo > capacidade:
            inc["historico"].append(f"{d}: sem capacidade para '{acao}', ficou aguardando")
            acao = "aguardar"
            custo = 0
        capacidade -= custo
        if acao != inc["acao"]:
            inc["historico"].append(f"{d}: ação → {acao}")
        inc["acao"] = acao
    for inc_id in set(acoes_dec) - {i["id"] for i in abertos}:
        eventos.append(_evento("extracao", "info", f"Decisão para {inc_id} ignorada: incidente não está aberto"))

    # 2) evolução dos incidentes abertos
    for inc in abertos:
        inc["dias"] += 1
        fonte, acao = inc["fonte"], inc["acao"]
        alt_existe = any(i["alt"] and i["fonte"] == fonte for i in config.INDICADORES.values())
        ex["fontes"][fonte]["alternativa_ligada"] = acao == "fonte_alternativa" and alt_existe
        if acao == "fonte_alternativa" and not alt_existe:
            inc["historico"].append(f"{d}: {config.FONTES[fonte]['nome']} não tem fonte alternativa")
        if acao == "corrigir_conector":
            inc["esforco"] += 1
        if inc["tipo"] == "falha_real":
            resolveu = real[fonte][0]
        elif inc["tipo"] == "mudanca_formato" and acao == "corrigir_conector":
            resolveu = rng(d, inc["id"]).random() < min(0.95, 0.25 * inc["esforco"] + 0.05 * (ex["equipe"] - 3))
        else:
            p = PROB_RESOLVER.get((inc["tipo"], acao), PROB_RESOLVER.get((inc["tipo"], "aguardar"), 0.3))
            resolveu = rng(d, inc["id"]).random() < p
        if acao == "escalar":
            estado["alertas"].setdefault(f"ESCALA-{inc['id']}", {
                "titulo": f"Extração pede reforço para {inc['id']} ({config.FONTES[fonte]['nome']})",
                "area": "executivos", "sev": "media", "aberto_em": d.isoformat(),
                "corpo": "A equipe de Extração escalou o incidente. Executivos: avaliem aumentar "
                         "`equipe_extracao` ou `orcamento_extracao_dia` na decisão do dia."})
        if resolveu:
            inc["estado"] = "resolvido"
            inc["resolvido_em"] = d.isoformat()
            inc["historico"].append(f"{d}: resolvido ({acao})")
            ex["fontes"][fonte]["alternativa_ligada"] = False
            estado["alertas"].pop(f"ESCALA-{inc['id']}", None)
            eventos.append(_evento("extracao", "resolvido", f"{inc['id']} resolvido: {config.FONTES[fonte]['nome']} "
                                   f"voltou após {inc['dias']} dia(s) ({acao})", chave=inc["id"]))

    # 3) novos incidentes: falhas reais e o acaso do dia (mais provável com dívida técnica alta)
    com_incidente = {i["fonte"] for i in estado["incidentes"] if i["estado"] == "aberto"}
    for fonte, meta in config.FONTES.items():
        ok, motivo = real[fonte]
        if not ok and not any(i["fonte"] == fonte and i["tipo"] == "falha_real" and i["estado"] == "aberto"
                              for i in estado["incidentes"]):
            inc = _novo_incidente(estado, fonte, "falha_real", d, motivo)
            inc["acao"] = padrao.get("falha_real", "corrigir_conector")
            com_incidente.add(fonte)
            eventos.append(_evento("extracao", "aberto", f"{inc['id']}: falha real em {meta['nome']}", chave=inc["id"]))
            continue
        if fonte in com_incidente:
            continue
        r = rng(d, "incidente", fonte)
        p = meta["prob_base"] * (1 + ex["divida_tecnica"] / 40)
        if r.random() < p:
            tipo = r.choices(["atraso", "fora_do_ar", "mudanca_formato"], weights=[50, 35, 15])[0]
            inc = _novo_incidente(estado, fonte, tipo, d, config.TIPOS_INCIDENTE[tipo])
            inc["acao"] = padrao.get(tipo, "aguardar")
            alt_existe = any(i["alt"] and i["fonte"] == fonte for i in config.INDICADORES.values())
            ex["fontes"][fonte]["alternativa_ligada"] = inc["acao"] == "fonte_alternativa" and alt_existe
            eventos.append(_evento("extracao", "aberto", f"{inc['id']}: {meta['nome']} — {config.TIPOS_INCIDENTE[tipo]}",
                                   chave=inc["id"]))

    # 4) o que a empresa consegue ver: só avança o que vem de fonte sem incidente
    bloqueadas = {i["fonte"] for i in estado["incidentes"] if i["estado"] == "aberto"}
    for fonte, meta in config.FONTES.items():
        if fonte in bloqueadas:
            continue
        for serie in meta["series"]:
            ex["fontes"][fonte]["liberado_ate"][serie] = _ultima_ate(mercado, serie, d)

    # 5) dívida técnica: cresce sozinha e com incidentes, cai com orçamento
    n_abertos = len(bloqueadas)
    ex["divida_tecnica"] = round(min(100.0, max(0.0, ex["divida_tecnica"] + 0.45 + 0.7 * n_abertos
                                                - ex["orcamento_dia"] / 1000)), 2)
    # incidentes resolvidos há mais de 30 dias saem do estado (o histórico fica em dados/dias)
    limite = (d - timedelta(days=30)).isoformat()
    estado["incidentes"] = [i for i in estado["incidentes"] if i["estado"] == "aberto" or i["resolvido_em"] >= limite]


# ====================================================================== dashboards
def _valor_indicador(ind: str, mercado: Mercado, ate: str | None, estado: dict) -> tuple[str, float] | None:
    """Valor do indicador usando só dados até `ate` (o que está liberado)."""
    if ate is None:
        return None
    meta = config.INDICADORES[ind]
    if ind == "cdi":
        u = mercado.ultimo("cdi", ate)
        return (u[0], round(((1 + u[1] / 100) ** 252 - 1) * 100, 2)) if u else None
    if ind == "ipca_12m":
        h = mercado.historico("ipca", ate, 12)
        if len(h) < 12:
            return None
        return h[-1][0], round((math.prod(1 + v / 100 for _, v in h) - 1) * 100, 2)
    if ind in ("taxa_pre", "taxa_ipca"):
        ativo = meta["ativo"]
        tipo, anos = config.TITULOS[ativo]
        venc = estado["fundo"]["posicoes"].get(ativo, {}).get("titulo") or mercado.escolher_titulo(tipo, anos, date.fromisoformat(ate))
        h = mercado.titulo(tipo, venc, ate) if venc else None
        return (h[0], h[1]) if h else None
    return mercado.ultimo(meta["serie"], ate)


def _estimar(ind: str, mercado: Mercado, base: tuple[str, float], liberado: dict, estado: dict) -> float:
    if ind == "cdi":
        sel = _valor_indicador("selic", mercado, liberado.get("selic"), estado)
        return round(sel[1] - 0.10, 2) if sel else base[1]
    if ind in ("dolar", "ibov", "bova11"):
        h = mercado.historico(config.INDICADORES[ind]["serie"], base[0], 6)
        if len(h) >= 2:
            ret = (h[-1][1] / h[0][1]) ** (1 / (len(h) - 1)) - 1
            return round(base[1] * (1 + ret), 4)
    return base[1]


def _passo_dashboards(estado: dict, d: date, mercado: Mercado, politicas: dict, decisao: dict, eventos: list,
                      decidir=None) -> dict:
    """`decidir(defasados)` é a reunião do time de Dashboards: recebe {indicador: dias de atraso} e devolve
    {indicador: estratégia}. Devolve as estratégias usadas no dia."""
    db = estado["dashboards"]
    pol = politicas["dashboards"]
    escolhas = dict((decisao.get("dashboards") or {}).get("estrategias", {}))
    fontes = estado["extracao"]["fontes"]
    liberado_por_ind = {}
    for ind, meta in config.INDICADORES.items():
        lib = fontes[meta["fonte"]]["liberado_ate"].get(meta["serie"])
        via = "principal"
        if meta["alt"] and fontes[meta["fonte"]]["alternativa_ligada"]:
            af, aserie = meta["alt"]
            alt_lib = fontes[af]["liberado_ate"].get(aserie)
            if alt_lib and (lib is None or alt_lib > lib):
                lib, via = alt_lib, "alternativa"
        liberado_por_ind[ind] = (lib, via)

    situacao = {}
    for ind, meta in config.INDICADORES.items():
        lib, via = liberado_por_ind[ind]
        if via == "alternativa":
            base = mercado.ultimo(meta["alt"][1], lib)
        else:
            base = _valor_indicador(ind, mercado, lib, estado)
        esperada = _data_esperada(meta["serie"], meta["fonte"], d)
        if meta.get("mensal"):
            atraso = 0 if base and base[0] >= esperada.isoformat() else 1
        else:
            atraso = calendario.defasagem(date.fromisoformat(base[0]) if base else None, esperada)
        situacao[ind] = (base, via, esperada, atraso)
    if decidir:
        escolhas = decidir({ind: s[3] for ind, s in situacao.items() if s[3] > 0}) | escolhas
    usadas = {}

    confs = []
    for ind, meta in config.INDICADORES.items():
        base, via, esperada, atraso = situacao[ind]
        anterior = db["indicadores"].get(ind, {})
        reg = {"nome": meta["nome"], "data_ref": base[0] if base else None, "defasagem": atraso, "via": via,
               "estrategia": None, "valor": base[1] if base else None, "confianca": 1.0 if via == "principal" else 0.9,
               "valor_anterior": anterior.get("valor")}
        if atraso > 0:
            est = escolhas.get(ind) or pol.get("por_indicador", {}).get(ind) or pol["estrategia_padrao"]
            reg["estrategia"] = est
            usadas[ind] = est
            if base is None or est == "suspender":
                reg["valor"], reg["confianca"] = None, 0.0
            elif est == "usar_ontem":
                reg["confianca"] = round(max(0.2, 1 - 0.2 * atraso), 2)
            else:  # estimar
                libs = {k: v[0] for k, v in liberado_por_ind.items()}
                reg["valor"] = _estimar(ind, mercado, base, libs, estado)
                reg["confianca"] = 0.6
                db["estimativas"].append({"indicador": ind, "data": esperada.isoformat(), "valor": reg["valor"]})
            chave = f"DEFAS-{ind}"
            if atraso >= 3:
                estado["alertas"].setdefault(chave, {
                    "titulo": f"Painel: {meta['nome']} defasado", "area": "dashboards", "sev": "media",
                    "aberto_em": d.isoformat(),
                    "corpo": f"O indicador está {atraso} dias úteis atrás. Estratégia atual: `{est}`. "
                             f"Avaliar trocar a estratégia ou pedir prioridade à Extração."})
                estado["alertas"][chave]["detalhe"] = f"{atraso} dias úteis de defasagem; estratégia `{est}`"
        else:
            estado["alertas"].pop(f"DEFAS-{ind}", None)
        db["indicadores"][ind] = reg
        confs.append(reg["confianca"])

    # estimativas antigas são conferidas quando o dado real aparece
    tol = pol.get("tolerancia_erro_estimativa", {})
    pendentes = []
    for e in db["estimativas"]:
        ind = e["indicador"]
        lib = liberado_por_ind[ind][0]
        if lib is None or lib < e["data"]:
            if e["data"] >= (d - timedelta(days=20)).isoformat():
                pendentes.append(e)
            continue
        real = _valor_indicador(ind, mercado, e["data"], estado)
        if not real or real[0] != e["data"]:
            continue
        erro = abs(e["valor"] - real[1]) / (abs(real[1]) if ind in ("dolar", "ibov", "bova11") else 1)
        if erro > tol.get(ind, 0.01):
            db["credibilidade"] = max(0.0, db["credibilidade"] - 0.05)
            times_.registrar_erro_estimativa(estado, ind, d)
            chave = f"ERRO-{ind}-{e['data']}"
            estado["alertas"][chave] = {
                "titulo": f"Painel errou {config.INDICADORES[ind]['nome']} de {e['data']}", "area": "dashboards",
                "sev": "media", "aberto_em": d.isoformat(), "expira": 5,
                "corpo": f"Estimado {e['valor']}, real {real[1]}. Os executivos decidiram com o número estimado. "
                         f"Revisar a estratégia `estimar` para este indicador."}
            eventos.append(_evento("dashboards", "alerta", f"Estimativa errada de {ind} em {e['data']}: "
                                   f"{e['valor']} vs real {real[1]}"))
        else:
            db["credibilidade"] = min(1.0, db["credibilidade"] + 0.01)
    db["estimativas"] = pendentes
    media = sum(confs) / len(confs)
    db["confianca_media"] = round(media, 3)
    db["credibilidade"] = round(min(1.0, max(0.0, db["credibilidade"] + 0.02 * (media - 0.95))), 3)
    return usadas


# ====================================================================== executivos + fundo
def _pesos(posicoes: dict) -> dict:
    total = sum(p["valor"] for p in posicoes.values())
    return {a: (p["valor"] / total if total else 0.0) for a, p in posicoes.items()}


def _passo_fundo(estado: dict, d: date, anterior: date, mercado: Mercado, politicas: dict, decisao: dict,
                 eventos: list, decidir=None) -> dict:
    """`decidir(ctx)` é a reunião dos executivos: devolve o bloco `executivos` da decisão do dia."""
    fundo, exe, g = estado["fundo"], estado["executivos"], estado["gestora"]
    pf, pg = politicas["fundo"], politicas["gestora"]

    # marcação a mercado com preços reais do dia
    fator_cdi = _fator_cdi(mercado, anterior, d)
    for ativo, pos in fundo["posicoes"].items():
        if ativo == "caixa":
            pos["valor"] *= fator_cdi
            continue
        preco, titulo = _preco_ativo(mercado, ativo, d, pos.get("titulo"))
        if preco is None:
            continue
        if titulo != pos.get("titulo") and pos.get("titulo") is not None:
            eventos.append(_evento("fundo", "info", f"{config.ATIVOS[ativo]}: troca de título {pos['titulo']} → {titulo}"))
            pos["preco"], pos["titulo"] = preco, titulo  # rolagem: mesmo valor, novo preço de referência
            continue
        if pos.get("preco"):
            pos["valor"] *= preco / pos["preco"]
        pos["preco"], pos["titulo"] = preco, titulo
    fundo["bench"] *= fator_cdi

    pl_bruto = sum(p["valor"] for p in fundo["posicoes"].values())
    dias = len(calendario.dias_uteis_entre(anterior, d)) or 1
    taxa = pl_bruto * pf["taxa_adm"] / 252 * dias
    fundo["posicoes"]["caixa"]["valor"] -= taxa
    pl = pl_bruto - taxa
    cota_ant = fundo["cota"]
    fundo["cota"] = pl / fundo["cotas"]

    # cotistas: reagem ao desempenho contra o CDI e à credibilidade da casa
    hist = fundo.setdefault("hist_cota", [])
    hist.append([d.isoformat(), fundo["cota"], fundo["bench"]])
    del hist[:-22]
    excesso = (hist[-1][1] / hist[0][1]) - (hist[-1][2] / hist[0][2]) if len(hist) > 1 else 0.0
    cred = estado["dashboards"]["credibilidade"]
    r = rng(d, "cotistas")
    fluxo_pct = max(-0.03, min(0.03, 0.15 * excesso + 0.002 * (cred - 0.75) + r.gauss(0, 0.0015)))
    fluxo = pl * fluxo_pct
    fundo["posicoes"]["caixa"]["valor"] += fluxo
    fundo["cotas"] += fluxo / fundo["cota"]
    fundo["fluxo_dia"] = round(fluxo, 2)
    if fluxo_pct < -0.01:
        estado["alertas"][f"RESGATE-{d}"] = {
            "titulo": f"Resgate relevante em {d}: {fluxo_pct:.2%} do PL", "area": "executivos", "sev": "alta",
            "aberto_em": d.isoformat(), "expira": 5,
            "corpo": f"Saíram R$ {-fluxo:,.0f}. Desempenho 21d vs CDI: {excesso:+.2%}; credibilidade dos painéis: {cred:.0%}."}

    # decisão dos executivos (aplicada no fechamento do dia em que foi tomada)
    dex = decisao.get("executivos") or {}
    indicadores = estado["dashboards"]["indicadores"]
    max_def = politicas["executivos"]["max_defasagem_para_operar"]
    congelados = set()
    for ind, meta in config.INDICADORES.items():
        reg = indicadores.get(ind, {})
        if meta["ativo"] and meta["ativo"] != "caixa" and (reg.get("valor") is None or reg.get("defasagem", 0) > max_def):
            congelados.add(meta["ativo"])
    if decidir:
        dex = decidir({"congelados": sorted(congelados), "excesso_21d": excesso, "fluxo_pct": fluxo_pct})
    pesos = _pesos(fundo["posicoes"])
    alvo = dict(exe["alvo"])
    if dex.get("alocacao"):
        alvo = dict(dex["alocacao"])
        exe["ultima_decisao"] = d.isoformat()
        exe["dias_sem_decisao"] = 0
        estado["alertas"].pop("EXEC-AUSENTE", None)
        for ativo in alvo:
            reg = next((indicadores.get(i, {}) for i, m in config.INDICADORES.items() if m["ativo"] == ativo), {})
            if abs(alvo[ativo] - exe["alvo"].get(ativo, 0)) > 0.02 and reg.get("confianca", 1) < 0.5:
                eventos.append(_evento("executivos", "alerta", f"Mudaram {config.ATIVOS[ativo]} olhando um número "
                                       f"com confiança {reg.get('confianca', 0):.0%}"))
    elif decisao or decidir:
        if dex or not decidir:  # com os times, "decisão" é quando o comitê muda alguma coisa
            exe["ultima_decisao"] = d.isoformat()
        exe["dias_sem_decisao"] = 0
        estado["alertas"].pop("EXEC-AUSENTE", None)
    else:
        exe["dias_sem_decisao"] += 1
        if exe["dias_sem_decisao"] >= 3:
            estado["alertas"].setdefault("EXEC-AUSENTE", {
                "titulo": "Executivos sem decisão registrada", "area": "executivos", "sev": "baixa",
                "aberto_em": d.isoformat(),
                "corpo": "Não há arquivo em `empresa/decisoes/` há 3 dias úteis ou mais. O fundo segue no piloto "
                         "automático (mantém o alvo e só rebalanceia por desvio)."})
    if congelados:
        # ativo sem número confiável fica onde está; o resto do alvo é redistribuído
        livre = 1 - sum(pesos[a] for a in congelados)
        base = sum(alvo[a] for a in alvo if a not in congelados)
        alvo = {a: (pesos[a] if a in congelados else (alvo[a] / base * livre if base else 0)) for a in alvo}
    exe["alvo"] = dict(dex["alocacao"]) if dex.get("alocacao") else exe["alvo"]
    exe["congelados"] = sorted(congelados)
    if "equipe_extracao" in dex:
        estado["extracao"]["equipe"] = int(dex["equipe_extracao"])
    if "orcamento_extracao_dia" in dex:
        estado["extracao"]["orcamento_dia"] = float(dex["orcamento_extracao_dia"])
    if decisao and (dex or not decidir):
        exe["decisoes_recentes"] = (exe["decisoes_recentes"] + [{"data": d.isoformat(), "autor": decisao.get("autor", "?"),
                                    "resumo": (dex.get("justificativa") or decisao.get("observacoes") or "")[:300]}])[-10:]

    # rebalanceamento: quando há decisão nova ou quando o desvio passa da tolerância
    pesos = _pesos(fundo["posicoes"])
    desvio = max(abs(pesos[a] - alvo[a]) for a in alvo)
    if dex.get("alocacao") or desvio > politicas["executivos"]["rebalancear_se_desvio_maior_que"] \
            or fundo["posicoes"]["caixa"]["valor"] < 0:
        total = sum(p["valor"] for p in fundo["posicoes"].values())
        giro = sum(abs(alvo[a] * total - fundo["posicoes"][a]["valor"]) for a in alvo) / 2
        custo = giro * pf["custo_transacao"]
        total -= custo
        for a in alvo:
            fundo["posicoes"][a]["valor"] = alvo[a] * total
        if giro > 0:
            eventos.append(_evento("fundo", "info", f"Rebalanceamento: giro R$ {times_._num(giro / 1e6, 1)} mi, custo R$ {times_._num(custo, 0)}"))
    fundo["pl"] = round(sum(p["valor"] for p in fundo["posicoes"].values()), 2)
    fundo["cota"] = fundo["pl"] / fundo["cotas"]
    fundo["retorno_dia"] = fundo["cota"] / cota_ant - 1

    # enquadramento
    pesos = _pesos(fundo["posicoes"])
    for ativo, (mn, mx) in pf["limites"].items():
        chave = f"DESENQ-{ativo}"
        if pesos[ativo] < mn - 1e-6 or pesos[ativo] > mx + 1e-6:
            estado["alertas"].setdefault(chave, {
                "titulo": f"Desenquadramento: {config.ATIVOS[ativo]}", "area": "executivos", "sev": "alta",
                "aberto_em": d.isoformat(), "corpo": ""})
            estado["alertas"][chave]["corpo"] = (f"Peso {pesos[ativo]:.1%} fora do limite {mn:.0%}–{mx:.0%}. "
                                                 f"Executivos precisam ajustar a alocação.")
        else:
            estado["alertas"].pop(chave, None)

    # gestora: receita da taxa de administração contra os custos da casa
    custo = (pg["custo_fixo_dia"] + estado["extracao"]["equipe"] * pg["custo_engenheiro_dia"]
             + estado["extracao"]["orcamento_dia"]) * dias
    g["receita_dia"], g["custo_dia"] = round(taxa, 2), round(custo, 2)
    g["caixa"] = round(g["caixa"] + taxa - custo, 2)
    if g["caixa"] < 0:
        estado["alertas"].setdefault("CRISE-CAIXA", {
            "titulo": "Caixa da gestora negativo", "area": "executivos", "sev": "alta", "aberto_em": d.isoformat(),
            "corpo": "A receita de taxa não cobre os custos. Reduzir equipe/orçamento ou recuperar PL."})
    else:
        estado["alertas"].pop("CRISE-CAIXA", None)
    return dex


# ====================================================================== alertas e eventos
def _evento(area: str, tipo: str, texto: str, chave: str | None = None) -> dict:
    return {"area": area, "tipo": tipo, "texto": texto, "chave": chave}


def _alertas_de_incidentes(estado: dict, d: date) -> None:
    for inc in estado["incidentes"]:
        chave = inc["id"]
        if inc["estado"] == "aberto":
            fonte = config.FONTES[inc["fonte"]]["nome"]
            sev = "alta" if inc["tipo"] in ("falha_real", "mudanca_formato") or inc["dias"] >= 3 else "media"
            estado["alertas"][chave] = {
                "titulo": f"{chave} · {fonte}: {config.TIPOS_INCIDENTE[inc['tipo']]}", "area": "extracao", "sev": sev,
                "aberto_em": inc["aberto_em"],
                "corpo": (f"**Fonte:** {fonte}\n**Tipo:** `{inc['tipo']}` — {inc['detalhe']}\n"
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


# ====================================================================== ata
def _narrar_dia(estado: dict, ata, eventos: list) -> None:
    """Os acontecimentos do dia entram na ata no horário da área, e o administrador fecha o dia."""
    for e in eventos:
        tipo = "alerta" if e["tipo"] in ("aberto", "alerta") else "evento"
        area = e["area"] if e["area"] in times_.PESSOAS else "fundo"
        quem = 1 if area in ("extracao", "dashboards") else 0
        if area == "executivos":
            quem = 2
        ata.diz(area, quem, e["texto"], tipo=tipo, hora=times_.HORA_EVENTO.get(area))
    f = estado["fundo"]
    n = times_._num
    ata.diz("fundo", 0, f"Fechamento: cota {n(f['cota'], 6)} ({'+' if f['retorno_dia'] >= 0 else ''}"
            f"{n(f['retorno_dia'] * 100)}% no dia), PL R$ {n(f['pl'] / 1e6, 1)} mi, fluxo de cotistas R$ "
            f"{n(f['fluxo_dia'] / 1e3, 0)} mil. Caixa da gestora R$ {n(estado['gestora']['caixa'] / 1e6)} mi.",
            tipo="fechamento")


# ====================================================================== o dia
def simular_dia(estado: dict, d: date, mercado: Mercado, politicas: dict, decisao: dict | None,
                controle: dict | None = None, times: bool = False) -> tuple[dict, dict]:
    """Avança a empresa até o fechamento do dia útil `d`. Devolve (novo_estado, registro_do_dia).

    Com `times`, os times de cada área decidem o dia (gestora/times.py) e `decisao` vira só a diretriz do
    conselho, que vale por cima do que o time decidiu. Sem `times`, vale só `decisao` (ou o piloto automático)."""
    estado = copy.deepcopy(estado)
    anterior = date.fromisoformat(estado["ultima_data"])
    if d <= anterior:
        raise ValueError(f"{d} já foi simulado (último: {anterior})")
    intervencao = decisao or {}
    eventos: list[dict] = []
    alertas_antes = set(estado["alertas"])
    ata = times_.Ata()

    if times:
        acoes = times_.extracao(estado, d, ata, intervencao)
        decisao = dict(intervencao, autor="conselho + times" if intervencao else "times",
                       extracao={"acoes": acoes | (intervencao.get("extracao") or {}).get("acoes", {})})
        dec_dash = lambda defasados: times_.dashboards(estado, d, defasados, ata, intervencao)  # noqa: E731
        dec_exec = lambda ctx: times_.executivos(estado, d, politicas, ctx, ata, intervencao)  # noqa: E731
    else:
        decisao, dec_dash, dec_exec = intervencao, None, None

    _passo_extracao(estado, d, mercado, controle, politicas, decisao, eventos)
    estrategias = _passo_dashboards(estado, d, mercado, politicas, decisao, eventos, dec_dash)
    dex = _passo_fundo(estado, d, anterior, mercado, politicas, decisao, eventos, dec_exec)
    _alertas_de_incidentes(estado, d)
    estado["ultima_data"] = d.isoformat()
    if times:
        _narrar_dia(estado, ata, eventos)

    abertos = set(estado["alertas"]) - alertas_antes
    fechados = alertas_antes - set(estado["alertas"])
    fundo = estado["fundo"]
    registro = {
        "data": d.isoformat(),
        "decisao": {"existe": bool(decisao), "autor": decisao.get("autor"), "intervencao": bool(intervencao)},
        "decisoes": {"extracao": (decisao.get("extracao") or {}).get("acoes", {}), "dashboards": estrategias,
                     "executivos": dex},
        "ata": ata.ordenada(),
        "eventos": eventos,
        "incidentes_do_dia": [{"id": i["id"], "fonte": i["fonte"], "tipo": i["tipo"]}
                              for i in estado["incidentes"] if i["estado"] == "aberto"],
        "alertas_abertos": sorted(abertos),
        "alertas_fechados": sorted(fechados),
        "resumo": {
            "cota": round(fundo["cota"], 8), "pl": fundo["pl"], "bench": round(fundo["bench"], 8),
            "retorno_dia": round(fundo["retorno_dia"], 6), "fluxo": fundo["fluxo_dia"],
            "pesos": {a: round(w, 4) for a, w in _pesos(fundo["posicoes"]).items()},
            "divida_tecnica": estado["extracao"]["divida_tecnica"],
            "incidentes_abertos": sum(i["estado"] == "aberto" for i in estado["incidentes"]),
            "credibilidade": estado["dashboards"]["credibilidade"],
            "confianca_media": estado["dashboards"]["confianca_media"],
            "caixa_gestora": estado["gestora"]["caixa"],
        },
    }
    return estado, registro
