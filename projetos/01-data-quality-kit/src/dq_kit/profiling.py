"""Perfil rápido de um dataset e leitura de fontes locais."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


def load(path: str | Path, table: str | None = None, query: str | None = None) -> pd.DataFrame:
    """Lê CSV, Parquet ou uma tabela/consulta de um banco SQLite."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".db", ".sqlite", ".sqlite3"}:
        if not (table or query):
            raise ValueError("para SQLite informe `table` ou `query`")
        with sqlite3.connect(path) as conn:
            if query:
                if not query.lstrip().lower().startswith(("select", "with")):
                    raise ValueError("apenas consultas de leitura (SELECT/WITH) são aceitas")
                return pd.read_sql_query(query, conn)
            if not table.replace("_", "").isalnum():
                raise ValueError(f"nome de tabela inválido: {table!r}")
            return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"formato não suportado: {suffix}")


def profile(df: pd.DataFrame, sample_size: int = 3) -> dict[str, Any]:
    columns = []
    for col in df.columns:
        s = df[col]
        info: dict[str, Any] = {
            "coluna": str(col),
            "tipo": str(s.dtype),
            "nulos": int(s.isna().sum()),
            "pct_nulos": round(100 * float(s.isna().mean()), 2) if len(s) else 0.0,
            "distintos": int(s.nunique(dropna=True)),
            "exemplos": [_plain(v) for v in s.dropna().unique()[:sample_size]],
        }
        if pd.api.types.is_numeric_dtype(s) and s.notna().any():
            info.update(minimo=_plain(s.min()), maximo=_plain(s.max()), media=round(float(s.mean()), 4))
        info["candidata_a_chave"] = info["distintos"] == len(s) and info["nulos"] == 0 and len(s) > 0
        columns.append(info)
    return {"linhas": int(len(df)), "colunas": columns}


def _plain(value: Any) -> Any:
    """Converte tipos numpy/pandas em tipos JSON-serializáveis."""
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value
