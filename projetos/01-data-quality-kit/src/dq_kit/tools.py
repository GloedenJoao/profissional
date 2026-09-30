"""Funções expostas como ferramentas para agentes de IA (ver mcp_server.py).

Ficam separadas do servidor MCP para poderem ser testadas sem o SDK e
reaproveitadas pela CLI. Todas devolvem dicionários JSON-serializáveis e
nunca escrevem nos dados de origem.
"""

from __future__ import annotations

from typing import Any

from . import checks as C
from .control_table import ControlTable
from .duplicates import find_duplicates
from .profiling import _plain, load, profile


def profile_dataset(path: str, table: str | None = None, query: str | None = None) -> dict[str, Any]:
    return profile(load(path, table, query))


def duplicates_dataset(path: str, keys: list[str], table: str | None = None,
                       query: str | None = None, max_groups: int = 20) -> dict[str, Any]:
    report = find_duplicates(load(path, table, query), keys)
    groups = report.to_frame().head(max_groups)
    return {
        "resumo": report.summary(),
        "grupos": [{k: _plain(v) for k, v in row.items()} for row in groups.to_dict(orient="records")],
    }


def check_dataset(path: str, specs: list[dict[str, Any]], table: str | None = None,
                  query: str | None = None) -> dict[str, Any]:
    df = load(path, table, query)
    results = C.run_checks(df, [C.from_spec(s) for s in specs])
    return {
        "aprovado": all(r.passed or r.severity == "warn" for r in results),
        "resultados": [
            {"check": r.check, "status": r.status, "severidade": r.severity,
             "observado": r.observed, "esperado": r.expected, "detalhe": r.detail}
            for r in results
        ],
    }


def control_summary(db_path: str) -> list[dict[str, Any]]:
    ct = ControlTable(db_path)
    try:
        return ct.summary()
    finally:
        ct.close()
