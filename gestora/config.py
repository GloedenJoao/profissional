"""Constantes da empresa: caminhos, fontes, indicadores e ativos."""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CENARIOS = RAIZ / "cenarios"
REPO = "GloedenJoao/profissional"

# Cenário ativo. "ao-vivo" é a empresa do dia a dia (dados/ e empresa/ na raiz); os outros moram em
# cenarios/<id>/ com a mesma estrutura e compartilham todo o código. `usar_cenario` troca os caminhos.
CENARIO_PADRAO = "ao-vivo"
CENARIO = CENARIO_PADRAO
SEMENTE = ""  # entra na semente do acaso: cenários diferentes não sorteiam os mesmos incidentes
DADOS = RAIZ / "dados"
SERIES = DADOS / "series"
DIAS = DADOS / "dias"
EMPRESA = RAIZ / "empresa"
DECISOES = EMPRESA / "decisoes"
DIARIO = EMPRESA / "diario"
POLITICAS = EMPRESA / "politicas.json"

NOME = "Capivara Asset"
FUNDO = "Capivara Multimercado FIC FIM"
AVISO = "Empresa e fundo fictícios. Dados de mercado reais; nada aqui é recomendação de investimento."

# Fontes (conectores). `series` são os arquivos em dados/series que cada uma alimenta.
# `prob_base` é a chance diária de falha no teste de estresse da Extração (antes da dívida técnica).
FONTES = {
    "bcb_sgs": {
        "nome": "BCB · SGS",
        "series": ["cdi", "selic", "dolar", "ipca"],
        "prob_base": 0.020,
    },
    "bcb_ptax": {
        "nome": "BCB · PTAX (Olinda)",
        "series": ["dolar_ptax"],
        "prob_base": 0.015,
    },
    "bcb_focus": {
        "nome": "BCB · Focus (Olinda)",
        "series": ["focus_ipca", "focus_selic"],
        "prob_base": 0.015,
    },
    "tesouro": {
        "nome": "Tesouro Direto (CSV)",
        "series": ["tesouro"],
        "prob_base": 0.030,
    },
    "yahoo": {
        "nome": "Yahoo Finance",
        "series": ["ibov", "bova11"],
        "prob_base": 0.035,
    },
    "b3": {
        "nome": "B3 · COTAHIST",
        "series": ["bova11_b3"],
        "prob_base": 0.020,
    },
}

# Indicadores que a área de Dashboards publica para os executivos.
# fonte/serie primária e, quando existe, a alternativa que a Extração pode ligar.
INDICADORES = {
    "cdi": {"nome": "CDI (% a.a.)", "fonte": "bcb_sgs", "serie": "cdi", "alt": None, "ativo": "caixa",
            "unidade": "% a.a.", "casas": 2},
    "selic": {"nome": "Selic meta (% a.a.)", "fonte": "bcb_sgs", "serie": "selic", "alt": None, "ativo": None,
              "unidade": "% a.a.", "casas": 2},
    "dolar": {"nome": "Dólar PTAX (R$)", "fonte": "bcb_sgs", "serie": "dolar", "alt": ("bcb_ptax", "dolar_ptax"),
              "ativo": "dolar", "unidade": "R$", "casas": 4},
    "ipca_12m": {"nome": "IPCA 12 meses (%)", "fonte": "bcb_sgs", "serie": "ipca", "alt": None, "ativo": None,
                 "mensal": True, "unidade": "%", "casas": 2},
    "focus_ipca": {"nome": "Focus IPCA do ano (%)", "fonte": "bcb_focus", "serie": "focus_ipca", "alt": None,
                   "ativo": None, "unidade": "%", "casas": 2},
    "focus_selic": {"nome": "Focus Selic fim do ano (%)", "fonte": "bcb_focus", "serie": "focus_selic", "alt": None,
                    "ativo": None, "unidade": "% a.a.", "casas": 2},
    "ibov": {"nome": "Ibovespa (pts)", "fonte": "yahoo", "serie": "ibov", "alt": None, "ativo": None,
             "unidade": "pts", "casas": 0},
    "bova11": {"nome": "BOVA11 (R$)", "fonte": "yahoo", "serie": "bova11", "alt": ("b3", "bova11_b3"), "ativo": "bolsa",
               "unidade": "R$", "casas": 2},
    "taxa_pre": {"nome": "Tesouro Prefixado (% a.a.)", "fonte": "tesouro", "serie": "tesouro", "alt": None,
                 "ativo": "prefixado", "unidade": "% a.a.", "casas": 2},
    "taxa_ipca": {"nome": "Tesouro IPCA+ (% a.a. real)", "fonte": "tesouro", "serie": "tesouro", "alt": None,
                  "ativo": "inflacao", "unidade": "% real", "casas": 2},
}

# Séries brutas: nome, unidade e nome curto (para as falas).
SERIES_INFO = {
    "cdi": ("CDI diário (SGS 12)", "% ao dia", "CDI"), "selic": ("Selic meta (SGS 432)", "% a.a.", "Selic"),
    "dolar": ("Dólar PTAX venda (SGS 1)", "R$", "dólar"), "ipca": ("IPCA mensal (SGS 433)", "% no mês", "IPCA"),
    "dolar_ptax": ("Dólar PTAX venda (Olinda)", "R$", "PTAX"),
    "focus_ipca": ("Focus · IPCA do ano (mediana)", "%", "Focus IPCA"),
    "focus_selic": ("Focus · Selic fim do ano (mediana)", "% a.a.", "Focus Selic"),
    "tesouro": ("Tesouro Direto · taxas e PUs", "% / R$", "Tesouro"), "ibov": ("Ibovespa (^BVSP)", "pts", "Ibovespa"),
    "bova11": ("BOVA11 (Yahoo)", "R$", "BOVA11"), "bova11_b3": ("BOVA11 (B3 COTAHIST)", "R$", "BOVA11 B3"),
}

# Quando cada série fica disponível: o que a empresa pode saber às 08h do dia D (nunca olhar o futuro).
# "d-1": fechamento do dia útil anterior (preços, CDI e PTAX de D saem só depois do horário das reuniões);
# "d": vale para o próprio dia (a Selic meta é definida antes pelo Copom);
# "semanal": Focus, publicado às segundas com a pesquisa até a sexta anterior;
# "mensal": IPCA do mês M, publicado pelo IBGE por volta do dia 10 de M+1 (usamos o dia 15, com folga).
PUBLICACAO = {"cdi": "d-1", "selic": "d", "dolar": "d-1", "ipca": "mensal", "dolar_ptax": "d-1",
              "focus_ipca": "semanal", "focus_selic": "semanal", "tesouro": "d-1", "ibov": "d-1", "bova11": "d-1",
              "bova11_b3": "d-1"}
REGRA_PUBLICACAO = {
    "d-1": "fechamento do dia útil anterior",
    "d": "vale para o próprio dia",
    "semanal": "sai às segundas, com a pesquisa até a sexta anterior",
    "mensal": "mês M sai até o dia 15 de M+1",
}


def formatar(ind: str, v: float | None) -> str:
    """Valor de um indicador com a unidade dele, em pt-BR."""
    if v is None:
        return "—"
    meta = INDICADORES[ind]
    s = f"{v:,.{meta['casas']}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    u = meta["unidade"]
    if u == "R$":
        return f"R$ {s}"
    if u == "pts":
        return f"{s} pts"
    return f"{s}{u}"  # "%", "% a.a.", "% real"


ATIVOS = {
    "caixa": "Caixa (CDI)",
    "prefixado": "Tesouro Prefixado",
    "inflacao": "Tesouro IPCA+",
    "dolar": "Dólar",
    "bolsa": "Ações (BOVA11)",
}

# Títulos do Tesouro usados pela carteira: tipo no CSV e prazo-alvo em anos.
TITULOS = {
    "prefixado": ("Tesouro Prefixado", 3),
    "inflacao": ("Tesouro IPCA+", 8),
}

ACOES_EXTRACAO = {
    "aguardar": "esperar a fonte voltar sozinha",
    "fonte_alternativa": "ligar a fonte alternativa (quando existe)",
    "corrigir_conector": "a equipe trabalha no conector até resolver",
    "escalar": "pedir ajuda aos executivos (mais orçamento/equipe)",
}
CUSTO_ACAO = {"aguardar": 0, "fonte_alternativa": 1, "corrigir_conector": 2, "escalar": 0}

ESTRATEGIAS_DASHBOARD = {
    "usar_ontem": "repete o último valor conhecido, com aviso de defasagem",
    "estimar": "estima o valor de hoje a partir de outras séries",
    "suspender": "não publica o número (executivos não decidem sobre ele)",
}

TIPOS_INCIDENTE = {
    "atraso": "a fonte publicou atrasado",
    "fora_do_ar": "a fonte saiu do ar",
    "mudanca_formato": "a fonte mudou o formato e o conector quebrou",
    "falha_real": "problema real: a fonte não entregou o dado esperado",
}


# ====================================================================== cenários
AO_VIVO = {
    "id": CENARIO_PADRAO,
    "nome": "Experimento",
    "descricao": "A empresa funcionando no presente: fecha sozinha de segunda a sexta às 08h, com os dados reais do "
                 "dia útil anterior.",
    "modo": "diario",
    "dados": "dados",
    "empresa": "empresa",
    "issues": True,
    "times": True,
}


def listar_cenarios() -> list[dict]:
    """O cenário ao vivo e os cenários paralelos declarados em cenarios/<id>/cenario.json."""
    itens = [dict(AO_VIVO)]
    for arq in sorted(CENARIOS.glob("*/cenario.json")):
        cid = arq.parent.name
        meta = json.loads(arq.read_text(encoding="utf-8"))
        rel = arq.parent.relative_to(RAIZ).as_posix()
        itens.append({"modo": "simulacao", "issues": False, "times": True, **meta, "id": cid,
                      "dados": f"{rel}/dados", "empresa": f"{rel}/empresa"})
    return itens


def cenario(cid: str | None = None) -> dict:
    cid = cid or CENARIO
    for c in listar_cenarios():
        if c["id"] == cid:
            return c
    raise SystemExit(f"cenário desconhecido: {cid} (existem: {', '.join(c['id'] for c in listar_cenarios())})")


def usar_cenario(cid: str) -> dict:
    """Aponta os caminhos de dados/ e empresa/ para o cenário `cid`."""
    global CENARIO, SEMENTE, DADOS, SERIES, DIAS, EMPRESA, DECISOES, DIARIO, POLITICAS
    meta = cenario(cid)
    CENARIO = meta["id"]
    SEMENTE = "" if CENARIO == CENARIO_PADRAO else CENARIO
    DADOS = RAIZ / meta["dados"]
    SERIES, DIAS = DADOS / "series", DADOS / "dias"
    EMPRESA = RAIZ / meta["empresa"]
    DECISOES, DIARIO, POLITICAS = EMPRESA / "decisoes", EMPRESA / "diario", EMPRESA / "politicas.json"
    return meta


def caminho_repo(caminho: Path) -> str:
    """Caminho relativo à raiz do repositório, para montar links do GitHub."""
    try:
        return caminho.resolve().relative_to(RAIZ.resolve()).as_posix()
    except ValueError:
        return caminho.as_posix()
