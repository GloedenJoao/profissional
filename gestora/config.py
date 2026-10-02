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
# `defasagem` é quantos dias úteis de atraso são normais na publicação.
FONTES = {
    "bcb_sgs": {
        "nome": "BCB · SGS",
        "series": ["cdi", "selic", "dolar", "ipca"],
        "defasagem": 0,
        "prob_base": 0.020,
    },
    "bcb_ptax": {
        "nome": "BCB · PTAX (Olinda)",
        "series": ["dolar_ptax"],
        "defasagem": 0,
        "prob_base": 0.015,
    },
    "bcb_focus": {
        "nome": "BCB · Focus (Olinda)",
        "series": ["focus_ipca", "focus_selic"],
        "defasagem": 5,
        "prob_base": 0.015,
    },
    "tesouro": {
        "nome": "Tesouro Direto (CSV)",
        "series": ["tesouro"],
        "defasagem": 1,
        "prob_base": 0.030,
    },
    "yahoo": {
        "nome": "Yahoo Finance",
        "series": ["ibov", "bova11"],
        "defasagem": 0,
        "prob_base": 0.035,
    },
    "b3": {
        "nome": "B3 · COTAHIST",
        "series": ["bova11_b3"],
        "defasagem": 0,
        "prob_base": 0.020,
    },
}

# Indicadores que a área de Dashboards publica para os executivos.
# fonte/serie primária e, quando existe, a alternativa que a Extração pode ligar.
INDICADORES = {
    "cdi": {"nome": "CDI (% a.a.)", "fonte": "bcb_sgs", "serie": "cdi", "alt": None, "ativo": "caixa"},
    "selic": {"nome": "Selic meta (% a.a.)", "fonte": "bcb_sgs", "serie": "selic", "alt": None, "ativo": None},
    "dolar": {"nome": "Dólar PTAX (R$)", "fonte": "bcb_sgs", "serie": "dolar", "alt": ("bcb_ptax", "dolar_ptax"), "ativo": "dolar"},
    "ipca_12m": {"nome": "IPCA 12 meses (%)", "fonte": "bcb_sgs", "serie": "ipca", "alt": None, "ativo": None, "mensal": True},
    "focus_ipca": {"nome": "Focus IPCA do ano (%)", "fonte": "bcb_focus", "serie": "focus_ipca", "alt": None, "ativo": None},
    "focus_selic": {"nome": "Focus Selic fim do ano (%)", "fonte": "bcb_focus", "serie": "focus_selic", "alt": None, "ativo": None},
    "ibov": {"nome": "Ibovespa (pts)", "fonte": "yahoo", "serie": "ibov", "alt": None, "ativo": None},
    "bova11": {"nome": "BOVA11 (R$)", "fonte": "yahoo", "serie": "bova11", "alt": ("b3", "bova11_b3"), "ativo": "bolsa"},
    "taxa_pre": {"nome": "Tesouro Prefixado (% a.a.)", "fonte": "tesouro", "serie": "tesouro", "alt": None, "ativo": "prefixado"},
    "taxa_ipca": {"nome": "Tesouro IPCA+ (% a.a. real)", "fonte": "tesouro", "serie": "tesouro", "alt": None, "ativo": "inflacao"},
}

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
    "falha_real": "o conector falhou de verdade nesta extração",
}


# ====================================================================== cenários
AO_VIVO = {
    "id": CENARIO_PADRAO,
    "nome": "Dia a dia",
    "descricao": "A empresa do dia a dia: fecha sozinha de segunda a sexta, com os times decidindo sobre os dados "
                 "reais do dia anterior.",
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
