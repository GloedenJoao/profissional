"""Validação das políticas e das diretrizes do conselho (arquivos em decisoes/, opcionais)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from . import armazem, config

CAMPOS_TOPO = {"data", "autor", "extracao", "dashboards", "executivos", "observacoes"}


def validar_politicas(p: dict) -> list[str]:
    erros = []
    for tipo, acao in p["extracao"]["acao_padrao"].items():
        if tipo not in config.TIPOS_INCIDENTE:
            erros.append(f"politicas.extracao: tipo de incidente desconhecido {tipo}")
        if acao not in config.ACOES_EXTRACAO:
            erros.append(f"politicas.extracao: ação desconhecida {acao}")
    d = p["dashboards"]
    for ind, est in [("padrao", d["estrategia_padrao"]), *d.get("por_indicador", {}).items()]:
        if est not in config.ESTRATEGIAS_DASHBOARD:
            erros.append(f"politicas.dashboards: estratégia desconhecida {est} ({ind})")
        if ind != "padrao" and ind not in config.INDICADORES:
            erros.append(f"politicas.dashboards: indicador desconhecido {ind}")
    lim = p["fundo"]["limites"]
    if set(lim) != set(config.ATIVOS):
        erros.append(f"politicas.fundo.limites precisa ter exatamente {sorted(config.ATIVOS)}")
    for ativo, (mn, mx) in lim.items():
        if not 0 <= mn <= mx <= 1:
            erros.append(f"politicas.fundo.limites.{ativo}: faixa inválida {mn}..{mx}")
    erros += _validar_alocacao(p["fundo"]["alocacao_inicial"], lim, "politicas.fundo.alocacao_inicial")
    est = p["extracao"].get("estresse", {})
    if not isinstance(est.get("ativo", True), bool) or not 0 <= est.get("multiplicador", 1) <= 10:
        erros.append("politicas.extracao.estresse: `ativo` é true/false e `multiplicador` fica entre 0 e 10")
    mod = p["executivos"].get("modelo", {})
    for ativo in mod.get("sensibilidade", {}):
        if ativo not in config.ATIVOS or ativo == "caixa":
            erros.append(f"politicas.executivos.modelo.sensibilidade: ativo desconhecido {ativo}")
    for k, v in mod.items():
        if k != "sensibilidade" and (not isinstance(v, (int, float)) or v < 0):
            erros.append(f"politicas.executivos.modelo.{k}: precisa ser um número ≥ 0")
    for k in ("escala_premio_prefixado", "escala_juro_real", "escala_tendencia_bolsa", "escala_tendencia_dolar"):
        if k in mod and mod[k] == 0:
            erros.append(f"politicas.executivos.modelo.{k}: não pode ser zero (divide o sinal)")
    cot = p["fundo"].get("cotistas", {})
    if cot and not 0 < cot.get("limite", 0.03) <= 0.2:
        erros.append("politicas.fundo.cotistas.limite: fica entre 0 e 0,2")
    return erros


def _validar_alocacao(aloc: dict, limites: dict, onde: str) -> list[str]:
    erros = []
    if set(aloc) != set(config.ATIVOS):
        return [f"{onde}: precisa ter exatamente {sorted(config.ATIVOS)}"]
    if abs(sum(aloc.values()) - 1) > 0.001:
        erros.append(f"{onde}: pesos somam {sum(aloc.values()):.4f}, precisam somar 1")
    for ativo, w in aloc.items():
        mn, mx = limites[ativo]
        if not mn - 1e-9 <= w <= mx + 1e-9:
            erros.append(f"{onde}.{ativo}: {w:.2%} fora do limite {mn:.0%}..{mx:.0%}")
    return erros


def validar_decisao(dec: dict, politicas: dict, nome_arquivo: str, estado: dict | None = None) -> list[str]:
    erros = []
    onde = nome_arquivo
    extras = set(dec) - CAMPOS_TOPO
    if extras:
        erros.append(f"{onde}: campos desconhecidos {sorted(extras)}")
    try:
        if date.fromisoformat(dec.get("data", "")).isoformat() != Path(nome_arquivo).stem:
            erros.append(f"{onde}: campo data precisa ser igual ao nome do arquivo")
    except ValueError:
        erros.append(f"{onde}: campo data ausente ou inválido")
    abertos = None
    if estado:
        abertos = {i["id"] for i in estado.get("incidentes", []) if i["estado"] == "aberto"}
    for inc, acao in dec.get("extracao", {}).get("acoes", {}).items():
        if acao not in config.ACOES_EXTRACAO:
            erros.append(f"{onde}: ação {acao!r} para {inc} não existe ({', '.join(config.ACOES_EXTRACAO)})")
        if abertos is not None and inc not in abertos:
            erros.append(f"{onde}: incidente {inc} não está aberto")
    for ind, est in dec.get("dashboards", {}).get("estrategias", {}).items():
        if ind not in config.INDICADORES:
            erros.append(f"{onde}: indicador {ind!r} não existe")
        if est not in config.ESTRATEGIAS_DASHBOARD:
            erros.append(f"{onde}: estratégia {est!r} não existe ({', '.join(config.ESTRATEGIAS_DASHBOARD)})")
    ex = dec.get("executivos", {})
    if "alocacao" in ex:
        erros += _validar_alocacao(ex["alocacao"], politicas["fundo"]["limites"], f"{onde}: executivos.alocacao")
    g = politicas["gestora"]
    if "equipe_extracao" in ex and not (1 <= int(ex["equipe_extracao"]) <= g["equipe_max"]):
        erros.append(f"{onde}: equipe_extracao precisa ficar entre 1 e {g['equipe_max']}")
    if "orcamento_extracao_dia" in ex and not (0 <= float(ex["orcamento_extracao_dia"]) <= g["orcamento_max_dia"]):
        erros.append(f"{onde}: orcamento_extracao_dia precisa ficar entre 0 e {g['orcamento_max_dia']}")
    return erros


def carregar_decisao(d: date, pasta: Path | None = None) -> dict | None:
    return armazem.ler_json((pasta or config.DECISOES) / f"{d.isoformat()}.json")


def validar_repositorio() -> list[str]:
    """Valida políticas e todas as decisões ainda não aplicadas (data > último dia simulado)."""
    politicas = armazem.ler_json(config.POLITICAS)
    erros = validar_politicas(politicas)
    estado = armazem.ler_json(config.DADOS / "estado.json")
    ultima = estado["ultima_data"] if estado else ""
    for arq in sorted(config.DECISOES.glob("*.json")):
        if arq.stem <= ultima:
            continue  # já aplicada: vale a política da época
        erros += validar_decisao(armazem.ler_json(arq), politicas, arq.name, estado)
    return erros
