"""Tabela de controle: todo resultado de check vira uma linha auditável.

Localmente grava em SQLite. `hive_ddl()` devolve a DDL equivalente para
criar a mesma tabela no Hive, particionada por data de execução — é o formato
usado quando o framework roda no cluster.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .checks import CheckResult

COLUMNS = (
    "run_id", "pipeline", "step", "layer", "dataset", "check_name",
    "severity", "status", "observed", "expected", "detail", "executed_at",
)


@dataclass(frozen=True)
class ControlRecord:
    run_id: str
    pipeline: str
    step: str
    layer: str
    dataset: str
    result: CheckResult
    executed_at: datetime

    def as_row(self) -> tuple[Any, ...]:
        r = self.result
        return (
            self.run_id, self.pipeline, self.step, self.layer, self.dataset, r.check,
            r.severity, r.status, _dump(r.observed), _dump(r.expected), r.detail,
            self.executed_at.isoformat(timespec="seconds"),
        )


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)


class ControlTable:
    def __init__(self, path: str | Path = ":memory:", table: str = "dq_controle") -> None:
        self.table = table
        self.conn = sqlite3.connect(str(path))
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                run_id TEXT, pipeline TEXT, step TEXT, layer TEXT, dataset TEXT,
                check_name TEXT, severity TEXT, status TEXT, observed TEXT,
                expected TEXT, detail TEXT, executed_at TEXT
            )
            """
        )

    def write(self, records: Iterable[ControlRecord]) -> None:
        rows = [rec.as_row() for rec in records]
        if rows:
            placeholders = ", ".join("?" for _ in COLUMNS)
            self.conn.executemany(f"INSERT INTO {self.table} VALUES ({placeholders})", rows)
            self.conn.commit()

    def rows(self, run_id: str | None = None) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {self.table}"
        params: tuple[Any, ...] = ()
        if run_id:
            sql += " WHERE run_id = ?"
            params = (run_id,)
        cur = self.conn.execute(sql + " ORDER BY rowid", params)
        return [dict(zip(COLUMNS, row)) for row in cur.fetchall()]

    def summary(self) -> list[dict[str, Any]]:
        """Visão por execução: quantos checks passaram/falharam em cada camada."""
        cur = self.conn.execute(
            f"""
            SELECT run_id, pipeline, layer,
                   SUM(status = 'passou') AS passou,
                   SUM(status = 'falhou' AND severity = 'error') AS falhou_erro,
                   SUM(status = 'falhou' AND severity = 'warn') AS falhou_alerta
            FROM {self.table}
            GROUP BY run_id, pipeline, layer
            ORDER BY MIN(executed_at), MIN(rowid)
            """
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()


def hive_ddl(database: str = "governanca", table: str = "dq_controle") -> str:
    return f"""CREATE TABLE IF NOT EXISTS {database}.{table} (
    run_id      STRING,
    pipeline    STRING,
    step        STRING,
    layer       STRING COMMENT 'pre | durante | pos',
    dataset     STRING,
    check_name  STRING,
    severity    STRING COMMENT 'error | warn',
    status      STRING COMMENT 'passou | falhou',
    observed    STRING,
    expected    STRING,
    detail      STRING,
    executed_at TIMESTAMP
)
PARTITIONED BY (dt_execucao STRING)
STORED AS PARQUET"""
