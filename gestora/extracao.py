"""Extração real: roda cada conector, grava as séries e a tabela de controle da execução."""
from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path

from . import armazem, config, fontes


def _ultima_data(serie: str, pasta: Path) -> str | None:
    linhas = armazem.ler_serie(serie, pasta)
    return max((ln["data"] for ln in linhas), default=None)


def extrair(inicio: date, fim: date, conectores=None, pasta: Path | None = None) -> dict:
    """Extrai a janela [inicio, fim] de todas as fontes. Uma fonte que falha não derruba as outras."""
    conectores = conectores or fontes.CONECTORES
    pasta = pasta or config.SERIES
    controle = {"executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "janela": [inicio.isoformat(), fim.isoformat()], "fontes": {}}
    for fonte, conector in conectores.items():
        registro: dict = {"status": "ok", "erro": None, "linhas_novas": 0}
        try:
            series = conector(inicio, fim)
            vazias = [s for s, linhas in series.items() if not linhas and not armazem.ler_serie(s, pasta)]
            for serie, linhas in series.items():
                registro["linhas_novas"] += armazem.mesclar_serie(serie, linhas, pasta)
            if vazias:
                raise ValueError(f"nenhuma linha para {', '.join(vazias)}")
        except Exception as e:  # noqa: BLE001 - toda falha vira registro e incidente, nunca derruba o fechamento
            registro["status"] = "erro"
            registro["erro"] = f"{type(e).__name__}: {e}"[:500]
        registro["ultima_data"] = {s: _ultima_data(s, pasta) for s in config.FONTES[fonte]["series"]}
        controle["fontes"][fonte] = registro
    return controle


def registrar_historico(controle: dict, caminho: Path | None = None) -> None:
    caminho = caminho or (config.DADOS / "controle_extracao.csv")
    novo = not caminho.exists()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if novo:
            w.writerow(["executado_em", "fonte", "status", "linhas_novas", "ultima_data", "erro"])
        for fonte, r in controle["fontes"].items():
            ultima = min((d for d in r["ultima_data"].values() if d), default="")
            w.writerow([controle["executado_em"], fonte, r["status"], r["linhas_novas"], ultima, r["erro"] or ""])
