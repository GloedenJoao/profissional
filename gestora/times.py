"""Os times da Capivara Asset: quem decide o dia a dia da empresa.

Cada área tem um time com regras próprias, memória e uma reunião por dia. As reuniões acontecem dentro
do motor, na ordem em que a informação chega: a Extração triagem os incidentes de manhã, os Dashboards
decidem o que publicar com o que a Extração liberou e o Comitê de Executivos decide com os números que
os Dashboards publicaram (nunca com o mercado "de verdade"). Tudo o que é dito vai para a ata do dia,
que o site mostra no modo ao vivo.

O dono (João) não precisa decidir nada. Se quiser intervir, um arquivo em `empresa/decisoes/` vira
**diretriz do conselho**: o que estiver nele vale por cima da decisão do time, e a ata registra.

Tudo é determinístico (o acaso usa a semente do dia), então o mesmo dia sempre tem a mesma reunião.
"""
from __future__ import annotations

from datetime import date

from . import calendario, config

PESSOAS = {
    "extracao": [("Bia", "líder de Extração"), ("Téo", "engenheiro de plantão")],
    "dashboards": [("Caio", "líder de Dashboards"), ("Lia", "analista de dados")],
    "executivos": [("Helena", "CEO"), ("Rafael", "CIO"), ("Marta", "Risco")],
    "conselho": [("Conselho", "diretriz")],
    "fundo": [("Administrador", "fechamento do fundo")],
}
HORARIO = {"extracao": "08:00", "dashboards": "09:00", "executivos": "10:00", "fundo": "18:00"}
HORA_EVENTO = {"extracao": "08:40", "dashboards": "09:40", "executivos": "10:40", "fundo": "17:30"}

FONTE_DO_ATIVO = {"dolar": "dolar", "bolsa": "bova11", "prefixado": "taxa_pre", "inflacao": "taxa_ipca"}
PASSO_MAX = 0.05  # o comitê não mexe mais que 5 p.p. num ativo por reunião
MEMORIA = 40      # quantos números publicados o comitê guarda por indicador


def _pct(v: float, casas: int = 1) -> str:
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def _num(v: float | None, casas: int = 2) -> str:
    return "—" if v is None else f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _brl(v: float) -> str:
    return "R$ " + _num(v, 0)


class Ata:
    """As falas do dia, em ordem. Cada fala: hora, área, quem, texto e tipo (fala/decisao/evento/conselho)."""

    def __init__(self) -> None:
        self.falas: list[dict] = []
        self._min = {}

    def _hora(self, area: str, hora: str | None) -> str:
        base = hora or HORARIO.get(area, "12:00")
        h, m = map(int, base.split(":"))
        chave = (area, base)
        m += self._min.get(chave, 0)
        self._min[chave] = self._min.get(chave, 0) + 2  # cada fala "leva" dois minutos
        return f"{h + m // 60:02d}:{m % 60:02d}"

    def diz(self, area: str, pessoa: int, texto: str, tipo: str = "fala", hora: str | None = None) -> None:
        nome, papel = PESSOAS[area][pessoa]
        self.falas.append({"hora": self._hora(area, hora), "area": area, "quem": nome, "papel": papel,
                           "texto": texto, "tipo": tipo})

    def conselho(self, area: str, texto: str, autor: str | None = None) -> None:
        nome, papel = PESSOAS["conselho"][0]
        papel = f"diretriz de {autor}" if autor and autor != "conselho" else papel
        self.falas.append({"hora": self._hora(area, None), "area": area, "quem": nome, "papel": papel,
                           "texto": texto, "tipo": "conselho"})

    def ordenada(self) -> list[dict]:
        return sorted(self.falas, key=lambda f: f["hora"])  # sort estável: a ordem de fala se mantém


def memoria(estado: dict) -> dict:
    m = estado.setdefault("times", {})
    m.setdefault("serie", {})
    m.setdefault("erros", {})
    m.setdefault("comite", {"ultimo": None})
    return m


# ====================================================================== Extração (08:00)
PRIORIDADE_FONTE = {"bcb_sgs": 0, "tesouro": 1, "yahoo": 2, "bcb_ptax": 3, "b3": 3, "bcb_focus": 4}


def _tem_alternativa(fonte: str) -> bool:
    return any(i["alt"] and i["fonte"] == fonte for i in config.INDICADORES.values())


def extracao(estado: dict, d: date, ata: Ata, intervencao: dict) -> dict:
    """Triagem dos incidentes abertos. Devolve {INC: ação} dentro da capacidade da equipe."""
    ex = estado["extracao"]
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    capacidade = ex["equipe"]
    if not abertos:
        if ex["divida_tecnica"] > 60:
            ata.diz("extracao", 0, f"Todas as fontes no ar, mas a dívida técnica está em {ex['divida_tecnica']:.0f}/100. "
                    "Quanto mais alta, mais a fonte quebra: vou pedir orçamento ao comitê.")
        else:
            ata.diz("extracao", 0, f"Bom dia! Nenhum incidente aberto. Dívida técnica {ex['divida_tecnica']:.0f}/100, "
                    f"equipe de {ex['equipe']}. Seguimos monitorando.")
        return {}
    ata.diz("extracao", 0, f"Bom dia. Temos {len(abertos)} incidente(s) aberto(s) e {capacidade} pessoa(s) na equipe. "
            "Vamos priorizar.")
    ordem = sorted(abertos, key=lambda i: (i["tipo"] != "falha_real", i["tipo"] != "mudanca_formato",
                                           PRIORIDADE_FONTE.get(i["fonte"], 9), i["aberto_em"]))
    acoes: dict[str, str] = {}
    humanas = (intervencao.get("extracao") or {}).get("acoes", {})
    for inc in ordem:
        fonte = config.FONTES[inc["fonte"]]["nome"]
        tipo, dias = inc["tipo"], inc["dias"]
        if inc["id"] in humanas:
            acao = humanas[inc["id"]]
            ata.conselho("extracao", f"Para {inc['id']} ({fonte}) a diretriz é `{acao}`.", intervencao.get("autor"))
            capacidade -= config.CUSTO_ACAO[acao]
            continue
        alt = _tem_alternativa(inc["fonte"])
        if tipo == "falha_real":
            acao, porque = "corrigir_conector", "falha real no conector: só resolve mexendo no código"
        elif tipo == "mudanca_formato":
            acao, porque = "corrigir_conector", "a fonte mudou o formato; esperar não resolve"
        elif tipo == "fora_do_ar":
            if alt and dias < 4:
                acao, porque = "fonte_alternativa", "tem fonte alternativa: o painel segue com número enquanto a fonte volta"
            elif dias >= 2:
                acao, porque = "corrigir_conector", f"fora do ar há {dias} dias, não dá mais para esperar"
            else:
                acao, porque = "aguardar", "sem alternativa; quedas assim costumam voltar em um ou dois dias"
        else:  # atraso
            if dias >= 3 and not alt:
                acao, porque = "corrigir_conector", f"atraso de {dias} dias já não é normal"
            elif dias >= 5:
                acao, porque = "corrigir_conector", f"{dias} dias de atraso mesmo com a alternativa: hora de mexer no conector"
            elif dias >= 1 and alt:
                acao, porque = "fonte_alternativa", "o atraso passou de um dia: liga a alternativa"
            else:
                acao, porque = "aguardar", "atraso costuma se resolver sozinho"
        custo = config.CUSTO_ACAO[acao]
        if custo > capacidade:
            if alt and acao == "corrigir_conector" and capacidade >= 1:
                acao, porque = "fonte_alternativa", "não tenho gente para corrigir agora; seguro com a alternativa"
            else:
                ata.diz("extracao", 0, f"{inc['id']} ({fonte}) precisava de `{acao}`, mas não sobrou gente. "
                        "Vou escalar para o comitê.")
                acao, porque = "escalar", "falta equipe"
                custo = 0
        capacidade -= config.CUSTO_ACAO[acao]
        quem = 1 if acao == "corrigir_conector" else 0
        aberto = "aberto ontem" if dias <= 1 else f"aberto há {dias} dias"
        if acao != inc["acao"] or dias == 0:
            ata.diz("extracao", quem, f"{inc['id']} · {fonte} ({config.TIPOS_INCIDENTE[tipo]}, {aberto}): "
                    f"`{acao}` — {porque}.", tipo="decisao")
        else:
            ata.diz("extracao", quem, f"{inc['id']} · {fonte} ({aberto}): seguimos com `{acao}`.")
        acoes[inc["id"]] = acao
    if capacidade > 0 and ex["divida_tecnica"] > 50:
        ata.diz("extracao", 1, f"Sobrou {capacidade} pessoa(s): usamos para pagar dívida técnica.")
    return acoes


# ====================================================================== Dashboards (09:00)
LENTOS = {"selic", "ipca_12m", "focus_ipca", "focus_selic"}
ESTIMAVEIS = {"cdi", "dolar", "ibov", "bova11"}


def dashboards(estado: dict, d: date, defasados: dict, ata: Ata, intervencao: dict) -> dict:
    """`defasados`: {indicador: dias de atraso}. Devolve {indicador: estratégia}."""
    db = estado["dashboards"]
    mem = memoria(estado)
    cred = db["credibilidade"]
    humanas = (intervencao.get("dashboards") or {}).get("estrategias", {})
    if not defasados:
        ata.diz("dashboards", 0, f"Todos os números chegaram em dia. Credibilidade dos painéis em {_pct(cred, 0)}. "
                "Publicando.")
        return {}
    nomes = ", ".join(config.INDICADORES[i]["nome"] for i in defasados)
    ata.diz("dashboards", 0, f"Faltam dados novos para: {nomes}. Credibilidade em {_pct(cred, 0)}.")
    out: dict[str, str] = {}
    for ind, atraso in defasados.items():
        nome = config.INDICADORES[ind]["nome"]
        if ind in humanas:
            out[ind] = humanas[ind]
            ata.conselho("dashboards", f"{nome}: publicar com `{humanas[ind]}`.", intervencao.get("autor"))
            continue
        errou = mem["erros"].get(ind)
        errou_recente = errou and len(calendario.dias_uteis_entre(date.fromisoformat(errou), d)) <= 10
        ativo = config.INDICADORES[ind]["ativo"]
        if ind in LENTOS:
            est, porque = "usar_ontem", "número que muda devagar; repetir o último é seguro"
        elif ind == "cdi":
            est, porque = "estimar", "o CDI acompanha a Selic, dá para estimar com folga"
        elif ind in ESTIMAVEIS and atraso == 1 and cred >= 0.7 and not errou_recente:
            est, porque = "estimar", "só um dia de atraso; estimo pela tendência da última semana"
        elif ativo and ativo != "caixa" and atraso >= 3:
            est, porque = "suspender", f"{atraso} dias sem dado: prefiro não publicar a induzir o comitê ao erro"
        else:
            est = "usar_ontem"
            porque = ("errei a estimativa disso há pouco, vou de último valor" if errou_recente
                      else "repito o último valor com aviso de defasagem")
        out[ind] = est
        ata.diz("dashboards", 1 if est == "estimar" else 0, f"{nome} ({atraso} dia(s) atrasado): `{est}` — {porque}.",
                tipo="decisao")
    return out


def registrar_erro_estimativa(estado: dict, ind: str, d: date) -> None:
    memoria(estado)["erros"][ind] = d.isoformat()


# ====================================================================== Executivos (10:00)
def _lembrar_numeros(estado: dict) -> None:
    """O comitê guarda os números publicados com dado real (não estimado) para ver tendência."""
    serie = memoria(estado)["serie"]
    for ind, reg in estado["dashboards"]["indicadores"].items():
        if reg.get("valor") is None or reg.get("estrategia") or not reg.get("data_ref"):
            continue
        s = serie.setdefault(ind, [])
        if s and s[-1][0] >= reg["data_ref"]:
            continue
        s.append([reg["data_ref"], reg["valor"]])
        del s[:-MEMORIA]


def _tendencia(estado: dict, ind: str, n: int) -> float | None:
    s = memoria(estado)["serie"].get(ind, [])
    if len(s) < max(3, n // 2):
        return None
    janela = s[-(n + 1):]
    return janela[-1][1] / janela[0][1] - 1


def _numero(estado: dict, ind: str) -> tuple[float | None, float]:
    reg = estado["dashboards"]["indicadores"].get(ind, {})
    return reg.get("valor"), reg.get("confianca", 0.0)


def _pautas(estado: dict, d: date, ctx: dict) -> list[str]:
    """O que faz o comitê de investimentos se reunir hoje (além da reunião de segunda)."""
    pautas = []
    alertas = estado["alertas"]
    if any(k.startswith("DESENQ-") for k in alertas):
        pautas.append("desenquadramento")
    if ctx["fluxo_pct"] < -0.01:
        pautas.append(f"resgate de {_pct(-ctx['fluxo_pct'])} do PL")
    if estado["gestora"]["caixa"] < 0:
        pautas.append("caixa da gestora negativo")
    if any(k.startswith("ESCALA-") for k in alertas):
        pautas.append("Extração pediu reforço")
    for ind in ("bova11", "dolar"):
        t = _tendencia(estado, ind, 1)
        if t is not None and abs(t) >= 0.03:
            pautas.append(f"{config.INDICADORES[ind]['nome']} {'+' if t > 0 else ''}{_pct(t)} no dia")
    return pautas


def _alvo_desejado(estado: dict, politicas: dict, ctx: dict, ata: Ata) -> tuple[dict, list[str]]:
    """A tese do CIO: para onde cada ativo deveria ir, com os números do painel e sua confiança."""
    lim = politicas["fundo"]["limites"]
    alvo = dict(estado["executivos"]["alvo"])
    novo = dict(alvo)
    motivos = []

    def quer(ativo: str, destino: float, porque: str) -> None:
        ind = FONTE_DO_ATIVO[ativo]
        _, conf = _numero(estado, ind)
        if ativo in ctx["congelados"] or conf < 0.5:
            ata.diz("executivos", 2, f"{config.ATIVOS[ativo]}: o número tem confiança {_pct(conf, 0)}. Não mexemos no que "
                    "não enxergamos.")
            return
        mn, mx = lim[ativo]
        destino = min(mx, max(mn, destino))
        passo = max(-PASSO_MAX, min(PASSO_MAX, destino - alvo[ativo]))
        if abs(passo) >= 0.02:
            novo[ativo] = round(alvo[ativo] + passo, 4)
            motivos.append(f"{config.ATIVOS[ativo]} {'+' if passo > 0 else ''}{passo * 100:.0f} p.p. ({porque})")

    taxa_ipca, _ = _numero(estado, "taxa_ipca")
    if taxa_ipca is not None:
        destino = 0.25 if taxa_ipca >= 7 else 0.2 if taxa_ipca >= 6 else 0.1 if taxa_ipca < 5 else 0.15
        ata.diz("executivos", 1, f"Tesouro IPCA+ pagando {_num(taxa_ipca)}% acima da inflação.")
        quer("inflacao", destino, f"juro real de {_num(taxa_ipca)}%")
    selic, _ = _numero(estado, "selic")
    focus_selic, _ = _numero(estado, "focus_selic")
    if selic is not None and focus_selic is not None:
        corte = selic - focus_selic
        if corte >= 0.75:
            destino, leitura = 0.25, f"mercado espera cortes de {_num(corte)} p.p. na Selic"
        elif corte <= -0.25:
            destino, leitura = 0.05, f"mercado espera alta de {_num(-corte)} p.p. na Selic"
        else:
            destino, leitura = 0.15, "Selic estável no horizonte"
        ata.diz("executivos", 1, f"Selic em {_num(selic)}% e Focus para o fim do ano em {_num(focus_selic)}%: {leitura}.")
        quer("prefixado", destino, leitura)
    t_bolsa = _tendencia(estado, "bova11", 20)
    if t_bolsa is not None:
        destino = 0.25 if t_bolsa > 0.04 else 0.2 if t_bolsa > 0 else 0.1 if t_bolsa < -0.04 else 0.15
        if ctx["defensivo"]:
            destino = min(destino, alvo["bolsa"])
        ata.diz("executivos", 1, f"Bolsa (BOVA11) {'+' if t_bolsa >= 0 else ''}{_pct(t_bolsa)} em 20 pregões.")
        quer("bolsa", destino, f"tendência de {'+' if t_bolsa >= 0 else ''}{_pct(t_bolsa)} em 20 pregões")
    t_dolar = _tendencia(estado, "dolar", 20)
    if t_dolar is not None:
        destino = 0.15 if t_dolar > 0.03 else 0.05 if t_dolar < -0.03 else 0.1
        if ctx["defensivo"]:
            destino = max(destino, alvo["dolar"])  # dólar é proteção: na defensiva não se reduz
        quer("dolar", destino, f"dólar {'+' if t_dolar >= 0 else ''}{_pct(t_dolar)} em 20 pregões")
    # o caixa fecha a conta, dentro do limite; se não couber, tira proporcionalmente do risco
    risco = [a for a in novo if a != "caixa"]
    novo["caixa"] = round(1 - sum(novo[a] for a in risco), 4)
    mn, mx = lim["caixa"]
    if novo["caixa"] < mn:
        falta = mn - novo["caixa"]
        soma = sum(novo[a] for a in risco)
        for a in risco:
            novo[a] = round(novo[a] - falta * novo[a] / soma, 4)
        novo["caixa"] = round(1 - sum(novo[a] for a in risco), 4)
    return novo, motivos


def _equipe_e_orcamento(estado: dict, d: date, politicas: dict, ata: Ata) -> dict:
    ex, g, pg = estado["extracao"], estado["gestora"], politicas["gestora"]
    custo_dia = pg["custo_fixo_dia"] + ex["equipe"] * pg["custo_engenheiro_dia"] + ex["orcamento_dia"]
    receita = g.get("receita_dia") or 0.0
    folego = g["caixa"] / custo_dia if custo_dia else 99
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    escalas = [k for k in estado["alertas"] if k.startswith("ESCALA-")]
    out = {}
    if g["caixa"] < 0 or folego < 15:
        if ex["orcamento_dia"] > 0:
            out["orcamento_extracao_dia"] = max(0.0, ex["orcamento_dia"] - 500)
            ata.diz("executivos", 0, f"Caixa da gestora em {_brl(g['caixa'])} ({folego:.0f} dias de custo). "
                    f"Cortamos o orçamento da Extração para {_brl(out['orcamento_extracao_dia'])}/dia.", tipo="decisao")
        elif ex["equipe"] > 2:
            out["equipe_extracao"] = ex["equipe"] - 1
            ata.diz("executivos", 0, f"Caixa apertado ({_brl(g['caixa'])}). Equipe de Extração cai para "
                    f"{out['equipe_extracao']}.", tipo="decisao")
        return out
    comite = memoria(estado)["comite"]
    ultima = comite.get("contratou")
    recente = ultima and len(calendario.dias_uteis_entre(date.fromisoformat(ultima), d)) < 10
    precisa = escalas or (len(abertos) >= 3 and ex["equipe"] < 4) or ex["divida_tecnica"] > 65
    if precisa and recente:
        ata.diz("executivos", 0, f"Contratamos para a Extração em {ultima[8:10]}/{ultima[5:7]}: esperamos a equipe nova "
                "render antes de contratar de novo.")
    elif precisa and ex["equipe"] < pg["equipe_max"] and folego > 40:
        out["equipe_extracao"] = ex["equipe"] + 1
        comite["contratou"] = d.isoformat()
        motivo = "a Extração pediu reforço" if escalas else (
            f"{len(abertos)} incidentes abertos" if len(abertos) >= 3 else f"dívida técnica em {ex['divida_tecnica']:.0f}")
        ata.diz("executivos", 0, f"Aprovado: +1 pessoa na Extração ({motivo}). Equipe vai para {out['equipe_extracao']}.",
                tipo="decisao")
    if ex["divida_tecnica"] > 50 and ex["orcamento_dia"] < pg["orcamento_max_dia"] and folego > 40:
        out["orcamento_extracao_dia"] = min(pg["orcamento_max_dia"], ex["orcamento_dia"] + 500)
        ata.diz("executivos", 0, f"Dívida técnica em {ex['divida_tecnica']:.0f}/100: orçamento da Extração sobe para "
                f"{_brl(out['orcamento_extracao_dia'])}/dia.", tipo="decisao")
    elif not abertos and ex["divida_tecnica"] < 25 and ex["equipe"] > 3 and receita < custo_dia:
        out["equipe_extracao"] = ex["equipe"] - 1
        ata.diz("executivos", 0, f"Fontes estáveis e dívida em {ex['divida_tecnica']:.0f}: a equipe de Extração volta para "
                f"{out['equipe_extracao']} para aliviar os custos.", tipo="decisao")
    return out


def executivos(estado: dict, d: date, politicas: dict, ctx: dict, ata: Ata, intervencao: dict) -> dict:
    """Reunião diária dos executivos e, às segundas ou quando há pauta, o comitê de investimentos.

    `ctx`: {"congelados", "excesso_21d", "fluxo_pct"}. Devolve o bloco `executivos` da decisão."""
    _lembrar_numeros(estado)
    mem = memoria(estado)
    db = estado["dashboards"]
    ctx = dict(ctx, defensivo=db["credibilidade"] < 0.6 or ctx["excesso_21d"] < -0.01)
    humano = intervencao.get("executivos") or {}
    out: dict = {}
    pautas = _pautas(estado, d, ctx)
    segunda = mem["comite"]["ultimo"] is None or date.fromisoformat(mem["comite"]["ultimo"]).isocalendar()[:2] != d.isocalendar()[:2]
    ata.diz("executivos", 0, f"Bom dia. Fundo {'+' if ctx['excesso_21d'] >= 0 else ''}{_pct(ctx['excesso_21d'], 2)} contra o "
            f"CDI em 21 dias, caixa da gestora {_brl(estado['gestora']['caixa'])}, credibilidade dos painéis "
            f"{_pct(db['credibilidade'], 0)}.")
    destaques = []
    for ind in ("dolar", "bova11", "taxa_pre", "taxa_ipca"):
        reg = db["indicadores"].get(ind, {})
        v, ant = reg.get("valor"), reg.get("valor_anterior")
        if v is None:
            continue
        nome = config.INDICADORES[ind]["nome"].split(" (")[0]
        var = f" ({'+' if v >= ant else ''}{_pct(v / ant - 1, 2)})" if ant else ""
        aviso = "" if reg.get("confianca", 1) >= 0.95 else f" [confiança {_pct(reg.get('confianca', 0), 0)}]"
        destaques.append(f"{nome} {_num(v)}{var}{aviso}")
    if destaques:
        ata.diz("executivos", 1, "No painel de hoje: " + "; ".join(destaques) + ".")
    if ctx["congelados"]:
        ata.diz("executivos", 2, "Sem número confiável para " + ", ".join(config.ATIVOS[a] for a in ctx["congelados"])
                + ": esses ficam como estão.")
    if humano.get("alocacao"):
        out["alocacao"] = humano["alocacao"]
        ata.conselho("executivos", "Alocação definida pelo conselho: " + ", ".join(
            f"{config.ATIVOS[a]} {_pct(w, 0)}" for a, w in humano["alocacao"].items()) + ".", intervencao.get("autor"))
    elif segunda or pautas:
        mem["comite"]["ultimo"] = d.isoformat()
        motivo = "reunião semanal" if segunda and not pautas else "pauta: " + "; ".join(pautas)
        ata.diz("executivos", 1, f"Comitê de investimentos ({motivo}).")
        if ctx["defensivo"]:
            ata.diz("executivos", 2, "Postura defensiva: " + ("os painéis estão pouco confiáveis" if db["credibilidade"] < 0.6
                    else "estamos perdendo do CDI") + ". Não aumentamos risco hoje.")
        novo, motivos = _alvo_desejado(estado, politicas, ctx, ata)
        if motivos:
            out["alocacao"] = novo
            ata.diz("executivos", 1, "Decidido: " + "; ".join(motivos) + ". Caixa fica em " + _pct(novo["caixa"], 0) + ".",
                    tipo="decisao")
        else:
            ata.diz("executivos", 1, "Carteira coerente com os números. Mantemos o alvo.", tipo="decisao")
    else:
        ata.diz("executivos", 1, "Sem pauta extraordinária: mantemos o alvo até o comitê de segunda.")
    for campo in ("equipe_extracao", "orcamento_extracao_dia"):
        if campo in humano:
            out[campo] = humano[campo]
    if "equipe_extracao" in humano or "orcamento_extracao_dia" in humano:
        ata.conselho("executivos", f"Equipe de Extração {humano.get('equipe_extracao', estado['extracao']['equipe'])}, "
                     f"orçamento {_brl(humano.get('orcamento_extracao_dia', estado['extracao']['orcamento_dia']))}/dia.",
                     intervencao.get("autor"))
    else:
        out.update(_equipe_e_orcamento(estado, d, politicas, ata))
    if humano.get("justificativa"):
        out["justificativa"] = humano["justificativa"]
    elif out:
        out["justificativa"] = " ".join(f["texto"] for f in ata.falas if f["area"] == "executivos"
                                        and f["tipo"] == "decisao")[:300]
    return out
