"""Análise de duplicidade com diagnóstico.

Saber que existem chaves repetidas é o começo. Para corrigir a origem é
preciso saber *como* elas se repetem:

- ``exata``: as linhas são idênticas — problema de carga (reprocessamento,
  append duplicado). Normalmente resolve com DISTINCT na origem.
- ``divergente``: mesma chave, valores diferentes — problema de modelagem ou
  de regra (histórico sem controle de vigência, join com granularidade
  errada). As colunas divergentes apontam onde olhar.

Evolução direta do analisador de duplicidades em Flask/React (ver
docs/estudos-de-caso/ferramentas-sql-analytics.md).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DuplicateGroup:
    key: tuple[Any, ...]
    rows: int
    kind: str  # "exata" | "divergente"
    divergent_columns: tuple[str, ...]


@dataclass
class DuplicateReport:
    keys: list[str]
    total_rows: int
    groups: list[DuplicateGroup] = field(default_factory=list)

    @property
    def duplicated_rows(self) -> int:
        return sum(g.rows for g in self.groups)

    @property
    def duplicated_keys(self) -> int:
        return len(self.groups)

    @property
    def by_kind(self) -> dict[str, int]:
        return dict(Counter(g.kind for g in self.groups))

    @property
    def column_divergence(self) -> dict[str, int]:
        """Em quantos grupos cada coluna diverge — ranking de onde investigar."""
        counter: Counter[str] = Counter()
        for g in self.groups:
            counter.update(g.divergent_columns)
        return dict(counter.most_common())

    def summary(self) -> dict[str, Any]:
        return {
            "chaves": self.keys,
            "linhas_total": self.total_rows,
            "linhas_duplicadas": self.duplicated_rows,
            "chaves_duplicadas": self.duplicated_keys,
            "pct_linhas_duplicadas": round(100 * self.duplicated_rows / self.total_rows, 2) if self.total_rows else 0.0,
            "por_tipo": self.by_kind,
            "colunas_divergentes": self.column_divergence,
        }

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {**dict(zip(self.keys, g.key)), "linhas": g.rows, "tipo": g.kind,
                 "colunas_divergentes": ", ".join(g.divergent_columns)}
                for g in self.groups
            ]
        )


def find_duplicates(df: pd.DataFrame, keys: list[str]) -> DuplicateReport:
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise KeyError(f"colunas-chave inexistentes: {missing}. Disponíveis: {list(df.columns)}")

    report = DuplicateReport(keys=list(keys), total_rows=len(df))
    dup = df[df.duplicated(subset=keys, keep=False)]
    if dup.empty:
        return report

    other = [c for c in df.columns if c not in keys]
    for key, group in dup.groupby(keys, dropna=False, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        divergent = tuple(c for c in other if group[c].nunique(dropna=False) > 1)
        report.groups.append(DuplicateGroup(key, len(group), "divergente" if divergent else "exata", divergent))
    return report
