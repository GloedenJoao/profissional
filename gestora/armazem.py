"""Leitura e escrita dos arquivos de dados (CSV das séries, JSON do estado)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import config


def ler_json(caminho: Path, padrao=None):
    if not caminho.exists():
        return padrao
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _chave(serie: str, linha: dict) -> tuple:
    if serie == "tesouro":
        return (linha["data"], linha["tipo"], linha["vencimento"])
    return (linha["data"],)


def colunas(serie: str) -> list[str]:
    return ["data", "tipo", "vencimento", "taxa", "pu"] if serie == "tesouro" else ["data", "valor"]


def ler_serie(serie: str, pasta: Path | None = None) -> list[dict]:
    caminho = (pasta or config.SERIES) / f"{serie}.csv"
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for ln in linhas:
        for c in ("valor", "taxa", "pu"):
            if c in ln:
                ln[c] = float(ln[c])
    return linhas


def mesclar_serie(serie: str, novas: list[dict], pasta: Path | None = None) -> int:
    """Upsert idempotente por chave. Devolve quantas linhas eram novas ou mudaram."""
    pasta = pasta or config.SERIES
    pasta.mkdir(parents=True, exist_ok=True)
    atuais = {_chave(serie, ln): ln for ln in ler_serie(serie, pasta)}
    mudou = 0
    for ln in novas:
        k = _chave(serie, ln)
        if atuais.get(k) != ln:
            mudou += 1
            atuais[k] = ln
    cols = colunas(serie)
    with (pasta / f"{serie}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for k in sorted(atuais):
            w.writerow({c: atuais[k][c] for c in cols})
    return mudou


def serie_por_data(serie: str, pasta: Path | None = None) -> dict[str, float]:
    return {ln["data"]: ln["valor"] for ln in ler_serie(serie, pasta)}
