"""Gera a base sintética, roda a mensuração e escreve o relatório.

    python -m mensuracao --saida relatorio_exemplo
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import timedelta
from pathlib import Path

from . import analise
from .simulacao import Parametros, gerar


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(prog="mensuracao")
    parser.add_argument("--saida", default="relatorio_exemplo", help="pasta de saída")
    parser.add_argument("--seed", type=int, default=Parametros.seed)
    args = parser.parse_args(argv)

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    p = Parametros(seed=args.seed)
    db = gerar(saida / "base_sintetica.db", p)

    with sqlite3.connect(db) as conn:
        nome, dt_inicio, _ = conn.execute("SELECT nome, dt_inicio, dt_fim FROM campanhas WHERE campanha_id = 1").fetchone()
        lift = analise.medir_lift(conn, 1, p.janela_dias)
        fim_janela = (p.inicio + timedelta(days=6 + p.janela_dias)).isoformat()
        canais = analise.atribuir_last_touch(conn, dt_inicio, fim_janela, lookback=30)
        curva = analise.curva_acumulada(conn, 1, p.janela_dias)

    (saida / "curva_acumulada.svg").write_text(analise.grafico_svg(curva), encoding="utf-8")
    texto = analise.relatorio(lift, canais, nome)
    texto += (
        f"\n---\n*Base sintética (seed {p.seed}): lift real configurado = {p.lift_real * 100:+.2f} p.p. "
        f"sobre taxa base de {p.taxa_base:.1%}. A mensuração acima não conhece esse valor; ele "
        f"{'está' if lift.ic95[0] <= p.lift_real <= lift.ic95[1] else 'NÃO está'} dentro do IC 95% estimado.*\n"
    )
    (saida / "relatorio.md").write_text(texto, encoding="utf-8")
    print(texto)
    return saida


if __name__ == "__main__":
    main()
