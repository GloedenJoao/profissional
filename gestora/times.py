"""Os times da Capivara Asset: as regras de decisão de cada área.

Cada função recebe a etapa do dia (gestora/rastro.py), decide com o que a etapa anterior entregou e grava no
rastro a regra que aplicou e a conta que fez. As falas citam os números dessas contas: nada é dito sem um
bloco do rastro que o sustente.

- Extração (08:00): triagem dos incidentes abertos, dentro da capacidade da equipe.
- Dashboards (09:00): o que publicar quando o dado não chegou.
- Comitê (10:00): pauta do dia, modelo de alocação e equipe/orçamento da Extração.

Um arquivo em `empresa/decisoes/AAAA-MM-DD.json` é diretriz do conselho: o que estiver nele vale por cima
do time naquele dia, e o rastro registra quem mandou.
"""
from __future__ import annotations

from datetime import date

from . import calendario, config
from .rastro import brl, cel, data, dm, mi, n_, num, pct, pp, sinal

# ====================================================================== Extração (08:00)
PRIORIDADE_FONTE = {"bcb_sgs": 0, "tesouro": 1, "yahoo": 2, "bcb_ptax": 3, "b3": 3, "bcb_focus": 4}

REGRAS_EXTRACAO = [
    "Falha real no conector: `corrigir_conector` (2 pontos). Só resolve quando a fonte real volta a publicar.",
    "Mudança de formato: `corrigir_conector` (2 pontos). Esperar não resolve.",
    "Fora do ar com fonte alternativa, até o 3º dia: `fonte_alternativa` (1 ponto).",
    "Fora do ar a partir do 2º dia (sem alternativa) ou do 4º (com alternativa): `corrigir_conector`.",
    "Fora do ar no 1º dia, sem alternativa: `aguardar` (quedas costumam voltar em 1 ou 2 dias).",
    "Atraso: `aguardar`; com alternativa, `fonte_alternativa` a partir do 2º dia; `corrigir_conector` a partir do "
    "3º dia sem alternativa ou do 5º com alternativa.",
    "Capacidade: cada pessoa da equipe vale 1 ponto por dia. Sem 2 pontos para corrigir, liga a alternativa se "
    "houver; sem nenhum ponto, `escalar` (pede reforço ao comitê).",
    "Ordem de atendimento: falha real, mudança de formato, depois pela importância da fonte "
    "(BCB SGS, Tesouro, Yahoo, PTAX/B3, Focus).",
    "Os dias contam a partir da abertura: o incidente aberto hoje é triado amanhã, no 1º dia.",
]


def tem_alternativa(fonte: str) -> bool:
    return any(i["alt"] and i["fonte"] == fonte for i in config.INDICADORES.values())


def _regra_incidente(tipo: str, dias: int, alt: bool) -> tuple[str, str]:
    """`dias`: dias úteis desde a abertura (1 na primeira triagem, no dia seguinte ao que o incidente abriu)."""
    if tipo == "falha_real":
        return "corrigir_conector", "falha real: só resolve no conector"
    if tipo == "mudanca_formato":
        return "corrigir_conector", "formato mudou: esperar não resolve"
    if tipo == "fora_do_ar":
        if alt and dias <= 3:
            return "fonte_alternativa", f"fora do ar ({dias}º dia) e há fonte alternativa"
        if dias >= 2:
            return "corrigir_conector", f"fora do ar há {dias} dias" + (" mesmo com a alternativa" if alt else "")
        return "aguardar", "fora do ar no 1º dia, sem alternativa"
    if dias >= 3 and not alt:
        return "corrigir_conector", f"atraso de {dias} dias, sem alternativa"
    if dias >= 5:
        return "corrigir_conector", f"atraso de {dias} dias mesmo com a alternativa"
    if dias >= 2 and alt:
        return "fonte_alternativa", f"atraso de {dias} dias e há alternativa"
    return "aguardar", f"atraso no {dias}º dia" + ("" if alt else ", sem alternativa")


def extracao(etapa, estado: dict, intervencao: dict) -> dict:
    """Triagem dos incidentes herdados. Devolve {INC: ação} dentro da capacidade da equipe."""
    ex = estado["extracao"]
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    capacidade = ex["equipe"]
    if not abertos:
        etapa.diz(0, f"Nenhum incidente herdado de ontem. Equipe de {n_(ex['equipe'], 'pessoa')} livre para monitorar "
                     f"as fontes; o orçamento de {brl(ex['orcamento_dia'])}/dia segue abatendo dívida técnica "
                     f"(hoje em {num(ex['divida_tecnica'], 1)}/100).")
        return {}
    humanas = (intervencao.get("extracao") or {}).get("acoes", {})
    ordem = sorted(abertos, key=lambda i: (i["tipo"] != "falha_real", i["tipo"] != "mudanca_formato",
                                           PRIORIDADE_FONTE.get(i["fonte"], 9), i["aberto_em"]))
    acoes: dict[str, str] = {}
    linhas = []
    for inc in ordem:
        alt = tem_alternativa(inc["fonte"])
        dias = inc["dias"]
        if inc["id"] in humanas:
            acao, porque, origem = humanas[inc["id"]], "diretriz do conselho", "conselho"
        else:
            acao, porque = _regra_incidente(inc["tipo"], dias, alt)
            origem = "decisao"
            custo = config.CUSTO_ACAO[acao]
            if custo > capacidade:
                if alt and acao == "corrigir_conector" and capacidade >= 1:
                    acao, porque = "fonte_alternativa", f"{porque}; sem 2 pontos livres, segura com a alternativa"
                else:
                    acao, porque = "escalar", f"{porque}; sem pontos livres na equipe"
        custo = config.CUSTO_ACAO[acao]
        antes = capacidade
        capacidade -= min(custo, max(capacidade, 0))
        acoes[inc["id"]] = acao
        linhas.append([inc["id"], config.FONTES[inc["fonte"]]["nome"], inc["tipo"], str(dias),
                       "sim" if alt else "não", porque, cel(f"`{acao}`", origem), f"{custo} ({antes}→{capacidade})"])
    b = etapa.tabela("Triagem dos incidentes herdados", ["Incidente", "Fonte", "Tipo", "Dias aberto", "Alternativa?",
                     "Regra aplicada", "Ação", "Pontos (livres)"], linhas,
                     nota=f"Capacidade do dia = equipe de {ex['equipe']} = {n_(ex['equipe'], 'ponto')}.")
    etapa.diz(0, f"Herdamos {n_(len(abertos), 'incidente')} e temos {n_(ex['equipe'], 'ponto')} de equipe. "
                 "Atendo na ordem: falha real, mudança de formato, depois pela importância da fonte.", bloco=b)
    for inc in ordem:
        acao = acoes[inc["id"]]
        nome = config.FONTES[inc["fonte"]]["nome"]
        if inc["id"] in humanas:
            etapa.conselho(f"{inc['id']} ({nome}): a diretriz manda `{acao}`.", intervencao.get("autor"), bloco=b)
            continue
        linha = next(ln for ln in linhas if ln[0] == inc["id"])
        mudou = acao != inc.get("acao")
        etapa.diz(1 if acao == "corrigir_conector" else 0,
                  f"{inc['id']} · {nome} ({config.TIPOS_INCIDENTE[inc['tipo']]}, {inc['dias']}º dia): "
                  f"{'passa para' if mudou else 'segue em'} `{acao}` — {linha[5]}.",
                  tipo="decisao" if mudou else "fala", bloco=b)
    return acoes


# ====================================================================== Dashboards (09:00)
LENTOS = {"selic", "ipca_12m", "focus_ipca", "focus_selic"}
ESTIMAVEIS = {"cdi", "dolar", "ibov", "bova11"}
REGRAS_DASHBOARDS = [
    "Número que muda devagar (Selic, IPCA 12m, Focus): `usar_ontem` — repetir o último é seguro.",
    "CDI: `estimar` pela Selic (o CDI fica cerca de 0,10 p.p. abaixo da Selic meta).",
    "Preço (dólar, Ibovespa, BOVA11) com 1 dia de atraso e credibilidade ≥ 70%, sem erro de estimativa "
    "nos últimos 10 dias úteis: `estimar` pela tendência da última semana.",
    "Preço de ativo da carteira com 3 dias ou mais de atraso: `suspender` (melhor não publicar do que induzir o "
    "comitê ao erro; o ativo fica congelado).",
    "Nos demais casos: `usar_ontem`, com aviso de defasagem.",
    "Confiança publicada: dado em dia 100%; via fonte alternativa 90%; `usar_ontem` 100% − 20 p.p. por dia de "
    "atraso (mínimo 20%); `estimar` 60%; `suspender` 0%.",
]


def memoria(estado: dict) -> dict:
    m = estado.setdefault("times", {})
    m.setdefault("erros", {})
    m.setdefault("comite", {"ultimo": None, "contratou": None})
    return m


def dashboards(etapa, estado: dict, d: date, defasados: dict, intervencao: dict) -> tuple[dict, str | None]:
    """`defasados`: {indicador: dias de atraso}. Devolve ({indicador: estratégia}, bloco)."""
    if not defasados:
        return {}, None
    mem = memoria(estado)
    cred = estado["dashboards"]["credibilidade"]
    humanas = (intervencao.get("dashboards") or {}).get("estrategias", {})
    out: dict[str, str] = {}
    linhas = []
    for ind, atraso in defasados.items():
        meta = config.INDICADORES[ind]
        errou = mem["erros"].get(ind)
        errou_recente = bool(errou) and len(calendario.dias_uteis_entre(date.fromisoformat(errou), d)) <= 10
        origem = "decisao"
        if ind in humanas:
            est, porque, origem = humanas[ind], "diretriz do conselho", "conselho"
        elif ind in LENTOS:
            est, porque = "usar_ontem", "muda devagar"
        elif ind == "cdi":
            est, porque = "estimar", "CDI acompanha a Selic"
        elif ind in ESTIMAVEIS and atraso == 1 and cred >= 0.7 and not errou_recente:
            est, porque = "estimar", f"1 dia de atraso, credibilidade {pct(cred, 0)} ≥ 70%"
        elif meta["ativo"] and meta["ativo"] != "caixa" and atraso >= 3:
            est, porque = "suspender", f"{atraso} dias sem preço de ativo da carteira"
        else:
            est = "usar_ontem"
            if errou_recente:
                porque = f"errou a estimativa em {dm(errou)}: volta a repetir o último"
            elif ind in ESTIMAVEIS and atraso == 1:
                porque = f"credibilidade {pct(cred, 0)} < 70%: não arrisca estimar"
            elif ind in ESTIMAVEIS:
                porque = f"{atraso} dias de atraso: estimar ficaria arriscado"
            elif ind in ("taxa_pre", "taxa_ipca"):
                porque = "taxa de título não se estima com segurança: repete a última"
            else:
                porque = "repete o último, com aviso de atraso"
        out[ind] = est
        linhas.append([meta["nome"], str(atraso), porque, cel(f"`{est}`", origem)])
    b = etapa.tabela("Estratégia para cada número atrasado", ["Indicador", "Dias de atraso", "Regra aplicada",
                     "Estratégia"], linhas)
    for ind, est in out.items():
        nome = config.INDICADORES[ind]["nome"]
        if ind in humanas:
            etapa.conselho(f"{nome}: publicar com `{est}`.", intervencao.get("autor"), bloco=b)
        else:
            porque = next(ln[2] for ln in linhas if ln[0] == nome)
            etapa.diz(1 if est == "estimar" else 0, f"{nome}: {n_(defasados[ind], 'dia')} de atraso → `{est}` "
                      f"({porque}).", tipo="decisao", bloco=b)
    return out, b


def registrar_erro_estimativa(estado: dict, ind: str, d: date) -> None:
    memoria(estado)["erros"][ind] = d.isoformat()


# ====================================================================== Comitê (10:00)
FONTE_DO_ATIVO = {"dolar": "dolar", "bolsa": "bova11", "prefixado": "taxa_pre", "inflacao": "taxa_ipca"}
MODELO_PADRAO = {
    "sensibilidade": {"prefixado": 0.10, "inflacao": 0.10, "dolar": 0.05, "bolsa": 0.10},
    "escala_premio_prefixado": 2.0,
    "juro_real_neutro": 5.5,
    "escala_juro_real": 2.0,
    "escala_tendencia_bolsa": 0.08,
    "escala_tendencia_dolar": 0.05,
    "passo_max": 0.05,
    "zona_morta": 0.02,
    "confianca_minima": 0.5,
    "gatilho_variacao_dia": 0.03,
    "gatilho_resgate": 0.01,
    "janela_tendencia": 20,
}
REGRAS_GESTORA = {
    "folego_minimo": 15,       # dias de custo que o caixa da gestora precisa cobrir antes de cortar
    "folego_para_gastar": 40,  # dias de custo para poder contratar ou subir orçamento
    "passo_orcamento": 500,
    "divida_para_orcamento": 50,
    "divida_para_contratar": 65,
    "divida_para_enxugar": 25,
    "dias_entre_contratacoes": 10,
}


def modelo(politicas: dict) -> dict:
    m = dict(MODELO_PADRAO)
    m.update(politicas.get("executivos", {}).get("modelo", {}))
    m["sensibilidade"] = {**MODELO_PADRAO["sensibilidade"], **m.get("sensibilidade", {})}
    return m


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _ind(estado: dict, ind: str) -> dict:
    return estado["dashboards"]["indicadores"].get(ind, {})


def sinais(estado: dict, politicas: dict) -> dict:
    """Sinal de cada ativo (−1 a +1) com a conta, só com números publicados no painel de hoje."""
    m = modelo(politicas)
    out = {}

    def conf(*inds):
        return min(_ind(estado, i).get("confianca", 0.0) for i in inds)

    pre, foc = _ind(estado, "taxa_pre").get("valor"), _ind(estado, "focus_selic").get("valor")
    if pre is not None and foc is not None:
        premio = pre - foc
        s = _clamp(premio / m["escala_premio_prefixado"])
        out["prefixado"] = {"sinal": s, "confianca": conf("taxa_pre", "focus_selic"),
                            "numeros": f"Prefixado {num(pre)}% · Focus Selic {num(foc)}%",
                            "conta": f"({num(pre)} − {num(foc)}) ÷ {num(m['escala_premio_prefixado'], 1)} = {sinal(s)}",
                            "leitura": f"paga {num(pre)}%, {num(abs(premio))} p.p. {'acima' if premio >= 0 else 'abaixo'} "
                                       f"da Selic que o mercado espera no fim do ano ({num(foc)}%)"}
    real = _ind(estado, "taxa_ipca").get("valor")
    if real is not None:
        s = _clamp((real - m["juro_real_neutro"]) / m["escala_juro_real"])
        out["inflacao"] = {"sinal": s, "confianca": conf("taxa_ipca"), "numeros": f"IPCA+ {num(real)}% real",
                           "conta": f"({num(real)} − {num(m['juro_real_neutro'], 1)}) ÷ {num(m['escala_juro_real'], 1)} "
                                    f"= {sinal(s)}",
                           "leitura": f"paga {num(real)}% acima da inflação, {num(abs(real - m['juro_real_neutro']))} "
                                      f"p.p. {'acima' if real >= m['juro_real_neutro'] else 'abaixo'} da nossa referência "
                                      f"de juro real ({num(m['juro_real_neutro'], 1)}%)"}
    for ativo, ind, chave in (("bolsa", "bova11", "escala_tendencia_bolsa"), ("dolar", "dolar", "escala_tendencia_dolar")):
        t = _ind(estado, ind).get("tendencia")
        if t:
            s = _clamp(t["valor"] / m[chave])
            out[ativo] = {"sinal": s, "confianca": conf(ind),
                          "numeros": f"{config.INDICADORES[ind]['nome'].split(' (')[0]} {pct(t['valor'], 1, True)} "
                                     f"em {t['n']} pregões",
                          "conta": f"{pct(t['valor'], 2, True)} ÷ {pct(m[chave], 0)} = {sinal(s)}",
                          "leitura": f"tendência de {pct(t['valor'], 1, True)} de {dm(t['de'])} a {dm(t['ate'])}"}
    return out


def _primeiro_dia_util_da_semana(d: date) -> bool:
    return calendario.dia_util_anterior(d).isocalendar()[:2] != d.isocalendar()[:2]


def pauta(estado: dict, d: date, politicas: dict, ctx: dict) -> tuple[list[list], list[str]]:
    """Gatilhos da reunião de investimentos: (linhas da tabela, motivos que dispararam)."""
    m = modelo(politicas)
    mem = memoria(estado)
    alertas = estado["alertas"]
    linhas, motivos = [], []

    def gatilho(nome, hoje, limite, dispara):
        linhas.append([nome, hoje, limite, cel("sim" if dispara else "não", "regra")])
        if dispara:
            motivos.append(nome.lower())

    gatilho("Reunião inaugural", "primeira reunião" if mem["comite"]["ultimo"] is None else
            f"última em {dm(mem['comite']['ultimo'])}", "nunca houve reunião", mem["comite"]["ultimo"] is None)
    gatilho("Reunião semanal", calendario.DIAS_SEMANA[d.weekday()], "primeiro dia útil da semana",
            mem["comite"]["ultimo"] is not None and _primeiro_dia_util_da_semana(d))
    fl = ctx["fluxo_ontem_pct"]
    gatilho("Resgate relevante ontem", pct(fl, 2, True) + " do PL", f"≤ −{pct(m['gatilho_resgate'], 0)}",
            fl <= -m["gatilho_resgate"])
    desenq = sorted(k[7:] for k in alertas if k.startswith("DESENQ-"))
    gatilho("Desenquadramento", ", ".join(desenq) or "nenhum", "algum ativo fora do limite", bool(desenq))
    caixa = estado["gestora"]["caixa"]
    gatilho("Caixa da gestora", brl(caixa), "negativo", caixa < 0)
    esc = sorted(k[7:] for k in alertas if k.startswith("ESCALA-"))
    gatilho("Pedido de reforço da Extração", ", ".join(esc) or "nenhum", "algum incidente escalado", bool(esc))
    for ind in ("bova11", "dolar"):
        reg = _ind(estado, ind)
        v, ant = reg.get("valor"), reg.get("valor_anterior")
        var = (v / ant - 1) if v is not None and ant else None
        gatilho(f"{config.INDICADORES[ind]['nome'].split(' (')[0]} no último pregão", pct(var, 2, True) if var is not None else "—",
                f"|variação| ≥ {pct(m['gatilho_variacao_dia'], 0)}",
                var is not None and abs(var) >= m["gatilho_variacao_dia"])
    return linhas, motivos


def alocacao(estado: dict, politicas: dict, ctx: dict) -> tuple[dict, list[list], dict]:
    """Modelo de alocação: alvo = neutro + sensibilidade × sinal, dentro das travas. Devolve (novo alvo, linhas da
    tabela, desfecho de cada ativo: {"sinal", "antes", "depois", "trava"})."""
    m = modelo(politicas)
    lim = politicas["fundo"]["limites"]
    neutro = politicas["fundo"]["alocacao_inicial"]
    alvo = dict(estado["executivos"]["alvo"])
    novo = dict(alvo)
    sg = sinais(estado, politicas)
    desfecho: dict[str, dict] = {}
    for ativo in ("prefixado", "inflacao", "bolsa", "dolar"):
        s = sg.get(ativo)
        sens = m["sensibilidade"][ativo]
        trava = ""
        if s is None:
            desejado = alvo[ativo]
            trava = ("histórico curto para medir a tendência" if ativo in ("bolsa", "dolar")
                     else "sem número publicado no painel")
        else:
            desejado = neutro[ativo] + sens * s["sinal"]
        final = desejado
        if s is not None:
            if ativo in ctx["congelados"]:
                final, trava = alvo[ativo], "congelado: o número está defasado ou suspenso"
            elif s["confianca"] < m["confianca_minima"]:
                final, trava = alvo[ativo], (f"o número tem confiança {pct(s['confianca'], 0)}, abaixo do mínimo de "
                                             f"{pct(m['confianca_minima'], 0)}")
            else:
                if ctx["defensivo"] and ativo == "bolsa" and final > alvo[ativo]:
                    final, trava = alvo[ativo], "postura defensiva: não aumenta bolsa"
                if ctx["defensivo"] and ativo == "dolar" and final < alvo[ativo]:
                    final, trava = alvo[ativo], "postura defensiva: dólar é proteção, não reduz"
                mn, mx = lim[ativo]
                if final < mn or final > mx:
                    trava = f"limite da política {pct(mn, 0)}–{pct(mx, 0)}"
                    final = min(mx, max(mn, final))
                passo = final - alvo[ativo]
                if abs(passo) > m["passo_max"]:
                    final = alvo[ativo] + (m["passo_max"] if passo > 0 else -m["passo_max"])
                    trava = f"passo máximo de {pp(m['passo_max'], 0)[1:]} por reunião"
                if abs(final - alvo[ativo]) < m["zona_morta"] - 1e-9:
                    final = alvo[ativo]
                    trava = trava or f"mudança menor que {pp(m['zona_morta'], 0)[1:]}: não vale o custo de girar"
        novo[ativo] = round(final, 4)
        desfecho[ativo] = {"s": s, "desejado": desejado, "trava": trava}
    # o caixa fecha a conta; se ficar abaixo do mínimo, os ativos de risco cedem proporcionalmente
    risco = [a for a in novo if a != "caixa"]
    novo["caixa"] = round(1 - sum(novo[a] for a in risco), 4)
    mn, _ = lim["caixa"]
    nota_caixa = "o que sobra"
    if novo["caixa"] < mn:
        falta = mn - novo["caixa"]
        soma = sum(novo[a] for a in risco)
        for a in risco:
            novo[a] = round(novo[a] - falta * novo[a] / soma, 4)
        novo["caixa"] = round(1 - sum(novo[a] for a in risco), 4)
        nota_caixa = f"mínimo de {pct(mn, 0)}: os outros cederam proporcionalmente"
        for a in risco:
            desfecho[a]["trava"] = (desfecho[a]["trava"] + "; " if desfecho[a]["trava"] else "") + "cedeu para o caixa mínimo"
    linhas = []
    for ativo in risco:
        s, des = desfecho[ativo]["s"], desfecho[ativo]
        mudou = abs(novo[ativo] - alvo[ativo]) > 1e-9
        des.update(antes=alvo[ativo], depois=novo[ativo], mudou=mudou)
        sens = m["sensibilidade"][ativo]
        linhas.append([
            config.ATIVOS[ativo],
            cel(s["numeros"] + f" · confiança {pct(s['confianca'], 0)}", "real") if s else "—",
            cel(s["conta"], "derivado") if s else "—",
            pct(neutro[ativo], 1),
            cel(f"{pct(neutro[ativo], 1)} + {num(sens * 100, 0)} p.p. × {sinal(s['sinal'])} = {pct(des['desejado'], 1)}",
                "derivado") if s else "—",
            pct(alvo[ativo], 1), cel(pct(novo[ativo], 1), "decisao"),
            des["trava"] or ("segue o modelo" if mudou else "mantém")])
    linhas.append([config.ATIVOS["caixa"], "—", "—", pct(neutro["caixa"], 1), "1 − soma dos outros",
                   pct(alvo["caixa"], 1), cel(pct(novo["caixa"], 1), "decisao"), nota_caixa])
    desfecho["caixa"] = {"antes": alvo["caixa"], "depois": novo["caixa"], "mudou": abs(novo["caixa"] - alvo["caixa"]) > 1e-9}
    return novo, linhas, desfecho


def equipe_e_orcamento(estado: dict, d: date, politicas: dict) -> tuple[dict, list[list], list[str], dict]:
    ex, g, pg = estado["extracao"], estado["gestora"], politicas["gestora"]
    R = REGRAS_GESTORA
    custo_dia = pg["custo_fixo_dia"] + ex["equipe"] * pg["custo_engenheiro_dia"] + ex["orcamento_dia"]
    folego = g["caixa"] / custo_dia if custo_dia else 999
    receita = g.get("receita_dia") or 0.0
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    escalas = [k for k in estado["alertas"] if k.startswith("ESCALA-")]
    mem = memoria(estado)["comite"]
    ultima = mem.get("contratou")
    recente = bool(ultima) and len(calendario.dias_uteis_entre(date.fromisoformat(ultima), d)) < R["dias_entre_contratacoes"]
    out: dict = {}
    frases: list[str] = []
    linhas = []

    def regra(nome, condicao, vale, efeito):
        linhas.append([nome, condicao, cel("sim" if vale else "não", "regra"), efeito if vale else "—"])

    corte = g["caixa"] < 0 or folego < R["folego_minimo"]
    efeito = "—"
    if corte:
        if ex["orcamento_dia"] > 0:
            out["orcamento_extracao_dia"] = max(0.0, ex["orcamento_dia"] - R["passo_orcamento"])
            efeito = f"orçamento {brl(ex['orcamento_dia'])} → {brl(out['orcamento_extracao_dia'])}/dia"
        elif ex["equipe"] > 2:
            out["equipe_extracao"] = ex["equipe"] - 1
            efeito = f"equipe {ex['equipe']} → {out['equipe_extracao']}"
        frases.append(f"o caixa da gestora cobre só {num(folego, 0)} dias de custo: {efeito}")
    regra("Cortar custos", f"fôlego {num(folego, 0)} dias < {R['folego_minimo']}?", corte, efeito)
    precisa = bool(escalas) or (len(abertos) >= 3 and ex["equipe"] < 4) or ex["divida_tecnica"] > R["divida_para_contratar"]
    pode = not corte and folego > R["folego_para_gastar"] and ex["equipe"] < pg["equipe_max"] and not recente
    contrata = precisa and pode
    if contrata:
        out["equipe_extracao"] = ex["equipe"] + 1
        mem["contratou"] = d.isoformat()
        motivo = ("a Extração escalou " + ", ".join(k[7:] for k in escalas) if escalas else
                  f"{len(abertos)} incidentes abertos" if len(abertos) >= 3 else f"dívida técnica {num(ex['divida_tecnica'], 0)}")
        frases.append(f"+1 pessoa na Extração ({motivo}): equipe {ex['equipe']} → {out['equipe_extracao']}")
    regra("Contratar para a Extração",
          f"escalada: {'sim' if escalas else 'não'}; incidentes {len(abertos)} (≥3 com equipe < 4); dívida "
          f"{num(ex['divida_tecnica'], 0)} (> {R['divida_para_contratar']}); fôlego {num(folego, 0)} (> {R['folego_para_gastar']})"
          + (f"; última contratação {dm(ultima)}" if ultima else ""), contrata,
          f"equipe {ex['equipe']} → {ex['equipe'] + 1}")
    sobe = (not corte and ex["divida_tecnica"] > R["divida_para_orcamento"] and folego > R["folego_para_gastar"]
            and ex["orcamento_dia"] < pg["orcamento_max_dia"])
    if sobe:
        out["orcamento_extracao_dia"] = min(pg["orcamento_max_dia"], ex["orcamento_dia"] + R["passo_orcamento"])
        frases.append(f"dívida técnica em {num(ex['divida_tecnica'], 0)}: orçamento {brl(ex['orcamento_dia'])} → "
                      f"{brl(out['orcamento_extracao_dia'])}/dia")
    regra("Subir orçamento da Extração", f"dívida {num(ex['divida_tecnica'], 0)} > {R['divida_para_orcamento']} e "
          f"fôlego {num(folego, 0)} > {R['folego_para_gastar']}?", sobe,
          f"orçamento +{brl(R['passo_orcamento'])}/dia")
    enxuga = (not corte and not contrata and not abertos and ex["divida_tecnica"] < R["divida_para_enxugar"]
              and ex["equipe"] > 3 and receita < custo_dia)
    if enxuga:
        out["equipe_extracao"] = ex["equipe"] - 1
        frases.append(f"fontes estáveis e dívida em {num(ex['divida_tecnica'], 0)}: equipe {ex['equipe']} → "
                      f"{out['equipe_extracao']} para aliviar custos")
    regra("Enxugar a Extração", f"sem incidentes, dívida {num(ex['divida_tecnica'], 0)} < {R['divida_para_enxugar']}, "
          f"equipe {ex['equipe']} > 3 e receita {brl(receita)} < custo {brl(custo_dia)}?", enxuga,
          f"equipe {ex['equipe']} → {ex['equipe'] - 1}")
    return out, linhas, frases, {"custo_dia": custo_dia, "folego": folego}


def comite(etapa, estado: dict, d: date, politicas: dict, ctx: dict, intervencao: dict) -> dict:
    """Reunião dos executivos. `ctx`: congelados, excesso, janela, fluxo_ontem_pct, cota_ontem, defensivo.
    Devolve o bloco `executivos` da decisão do dia."""
    db = estado["dashboards"]
    mem = memoria(estado)
    humano = intervencao.get("executivos") or {}
    out: dict = {}

    # abertura: o que o comitê está vendo
    linhas = []
    for ind, reg in db["indicadores"].items():
        if reg.get("valor") is None:
            v = cel("não publicado", "decisao")
        else:
            v = cel(config.formatar(ind, reg["valor"]), "derivado" if reg.get("estrategia") == "estimar" else "real",
                    "estimado pelos Dashboards" if reg.get("estrategia") == "estimar" else None)
        linhas.append([reg["nome"], v, data(reg.get("data_ref")), reg.get("estrategia") or "em dia",
                       pct(reg.get("confianca", 0), 0)])
    b_painel = etapa.tabela("O que o comitê recebeu dos Dashboards (09h)", ["Indicador", "Valor", "Referência",
                            "Situação", "Confiança"], linhas,
                            nota="O comitê só enxerga estes números: nunca o mercado diretamente.")
    exc, jan = ctx["excesso"], ctx["janela"]
    if jan == 0:
        abertura = (f"Bom dia. Primeiro dia do fundo: começamos com cota 1,000000 e patrimônio "
                    f"{mi(estado['fundo']['pl'])}, na alocação neutra da política.")
    else:
        abertura = (f"Bom dia. O fundo fechou ontem com cota {num(ctx['cota_ontem'], 6)}; desde {dm(ctx['desde'])} "
                    f"({jan} {'pregões' if jan > 1 else 'pregão'}) rendeu {pct(ctx['ret_fundo'], 2, True)} contra "
                    f"{pct(ctx['ret_cdi'], 2, True)} do CDI ({pp(exc, 2)}).")
    etapa.diz(0, abertura + f" Painel das 09h com confiança média {pct(db.get('confianca_media'), 0)} e credibilidade "
                 f"{pct(db['credibilidade'], 0)}.", bloco=b_painel)
    if ctx["congelados"]:
        etapa.diz(2, "Sem número confiável para " + ", ".join(config.ATIVOS[a] for a in ctx["congelados"])
                  + ": esses ativos ficam como estão hoje.", bloco=b_painel)

    # pauta
    linhas_p, motivos = pauta(estado, d, politicas, ctx)
    b_pauta = etapa.tabela("Pauta: há reunião de investimentos hoje?", ["Gatilho", "Hoje", "Dispara se", "Dispara?"],
                           linhas_p)
    reuniao = bool(motivos)
    if humano.get("alocacao"):
        out["alocacao"] = dict(humano["alocacao"])
        etapa.conselho("Alocação definida pelo conselho: " + ", ".join(
            f"{config.ATIVOS[a]} {pct(w, 1)}" for a, w in humano["alocacao"].items()) + ".", intervencao.get("autor"),
            bloco=b_pauta)
    elif reuniao:
        mem["comite"]["ultimo"] = d.isoformat()
        etapa.diz(1, "Reunião de investimentos hoje: " + "; ".join(motivos) + ".", bloco=b_pauta)
        if ctx["defensivo"]:
            etapa.diz(2, "Postura defensiva: " + ("credibilidade dos painéis abaixo de 60%"
                      if db["credibilidade"] < 0.6 else f"o fundo está {pp(exc, 2)} contra o CDI")
                      + ". Não aumentamos bolsa e não reduzimos dólar.", bloco=b_pauta)
        novo, linhas_m, desfecho = alocacao(estado, politicas, ctx)
        m = modelo(politicas)
        b_mod = etapa.tabela("Modelo de alocação: alvo = neutro + sensibilidade × sinal", [
            "Ativo", "Número do painel", "Sinal (−1 a +1)", "Neutro", "Desejado", "Alvo atual", "Novo alvo", "Trava"],
            linhas_m, nota=f"Travas: confiança mínima {pct(m['confianca_minima'], 0)}; limites da política; passo máximo "
                           f"{pp(m['passo_max'], 0)[1:]}; mudanças menores que {pp(m['zona_morta'], 0)[1:]} não giram a carteira.")
        for ativo in ("prefixado", "inflacao", "bolsa", "dolar"):
            des = desfecho[ativo]
            s = des["s"]
            if s is None:
                etapa.diz(1, f"{config.ATIVOS[ativo]}: {des['trava']}; fica em {pct(des['depois'], 1)}.", bloco=b_mod)
                continue
            fim = (f"alvo {pct(des['antes'], 1)} → {pct(des['depois'], 1)}" if des["mudou"] else
                   f"fica em {pct(des['depois'], 1)}")
            if des["trava"]:
                fim += f" ({des['trava']})"
            etapa.diz(2 if des["trava"] and not des["mudou"] and "confiança" in des["trava"] else 1,
                      f"{config.ATIVOS[ativo]}: {s['leitura']} → sinal {sinal(s['sinal'])} → {fim}.", bloco=b_mod)
        if any(des.get("mudou") for des in desfecho.values()):
            out["alocacao"] = novo
            etapa.diz(1, "Decidido. Novo alvo: " + ", ".join(f"{config.ATIVOS[a].split(' (')[0]} {pct(w, 1)}"
                                                             for a, w in novo.items()) + ".", tipo="decisao", bloco=b_mod)
        else:
            etapa.diz(1, "Nenhuma mudança passou pelas travas: o alvo fica como está.", tipo="decisao", bloco=b_mod)
    else:
        m = modelo(politicas)
        movs = "; ".join(f"{ln[0].replace(' no último pregão', '')} {ln[1]}" for ln in linhas_p
                         if ln[0].endswith(" no último pregão"))
        etapa.diz(1, f"Sem reunião de investimentos: não é o primeiro dia útil da semana e nenhum gatilho disparou "
                     f"(último pregão: {movs}; o gatilho é ±{pct(m['gatilho_variacao_dia'], 0)}). O alvo segue "
                     + ", ".join(f"{config.ATIVOS[a].split(' (')[0]} {pct(w, 1)}"
                                 for a, w in estado["executivos"]["alvo"].items()) + ".", bloco=b_pauta)

    # equipe e orçamento da Extração
    if "equipe_extracao" in humano or "orcamento_extracao_dia" in humano:
        for campo in ("equipe_extracao", "orcamento_extracao_dia"):
            if campo in humano:
                out[campo] = humano[campo]
        etapa.conselho(f"Equipe de Extração {humano.get('equipe_extracao', estado['extracao']['equipe'])}, orçamento "
                       f"{brl(humano.get('orcamento_extracao_dia', estado['extracao']['orcamento_dia']))}/dia.",
                       intervencao.get("autor"))
    else:
        mudou, linhas_g, frases, f = equipe_e_orcamento(estado, d, politicas)
        out.update(mudou)
        b_g = etapa.tabela("Equipe e orçamento da Extração", ["Regra", "Condição com os números de hoje", "Vale?",
                           "Efeito"], linhas_g,
                           nota=f"Custo diário da casa hoje: {brl(f['custo_dia'])}; caixa da gestora "
                                f"{brl(estado['gestora']['caixa'])} = {num(f['folego'], 0)} dias de fôlego.")
        if frases:
            etapa.diz(0, "Aprovado: " + "; ".join(frases) + ".", tipo="decisao", bloco=b_g)
        else:
            etapa.diz(0, f"Caixa da gestora {brl(estado['gestora']['caixa'])} cobre {num(f['folego'], 0)} dias de custo "
                         f"({brl(f['custo_dia'])}/dia). Equipe de {estado['extracao']['equipe']} e orçamento de "
                         f"{brl(estado['extracao']['orcamento_dia'])}/dia ficam como estão.", bloco=b_g)
    if humano.get("justificativa"):
        out["justificativa"] = humano["justificativa"]
    elif out:
        out["justificativa"] = " ".join(f["texto"] for f in etapa.rastro.falas
                                        if f["etapa"] == etapa.id and f["tipo"] in ("decisao", "conselho"))[:300]
    return out
