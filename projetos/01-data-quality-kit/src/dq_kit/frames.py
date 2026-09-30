"""Adaptadores de DataFrame.

Os checks nunca falam direto com pandas ou PySpark: eles pedem a um adaptador
operações pequenas (contar linhas, contar nulos, contar chaves repetidas...).
Assim o mesmo check roda local com pandas e no cluster com PySpark, sem
duplicar regra de negócio.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol


class FrameOps(Protocol):
    def columns(self) -> list[str]: ...
    def count(self) -> int: ...
    def null_count(self, column: str) -> int: ...
    def duplicated_row_count(self, keys: list[str]) -> int: ...
    def count_not_in(self, column: str, values: Iterable[Any]) -> int: ...
    def count_outside(self, column: str, min_value: Any = None, max_value: Any = None) -> int: ...
    def max_value(self, column: str) -> Any: ...
    def sum(self, column: str) -> float: ...


class PandasOps:
    def __init__(self, df: Any) -> None:
        self.df = df

    def columns(self) -> list[str]:
        return [str(c) for c in self.df.columns]

    def count(self) -> int:
        return int(len(self.df))

    def null_count(self, column: str) -> int:
        return int(self.df[column].isna().sum())

    def duplicated_row_count(self, keys: list[str]) -> int:
        return int(self.df.duplicated(subset=keys, keep=False).sum())

    def count_not_in(self, column: str, values: Iterable[Any]) -> int:
        series = self.df[column].dropna()
        return int((~series.isin(list(values))).sum())

    def count_outside(self, column: str, min_value: Any = None, max_value: Any = None) -> int:
        series = self.df[column].dropna()
        mask = series != series  # tudo False, preservando o índice
        if min_value is not None:
            mask |= series < min_value
        if max_value is not None:
            mask |= series > max_value
        return int(mask.sum())

    def max_value(self, column: str) -> Any:
        value = self.df[column].max()
        return None if value != value else value  # NaN -> None

    def sum(self, column: str) -> float:
        return float(self.df[column].sum())


class SparkOps:
    """Mesmas operações em PySpark. Importa pyspark só quando usado."""

    def __init__(self, df: Any) -> None:
        from pyspark.sql import functions as F  # noqa: N812

        self.df = df
        self.F = F

    def columns(self) -> list[str]:
        return list(self.df.columns)

    def count(self) -> int:
        return int(self.df.count())

    def null_count(self, column: str) -> int:
        return int(self.df.filter(self.F.col(column).isNull()).count())

    def duplicated_row_count(self, keys: list[str]) -> int:
        F = self.F
        row = (
            self.df.groupBy(*keys)
            .count()
            .filter(F.col("count") > 1)
            .agg(F.coalesce(F.sum("count"), F.lit(0)).alias("n"))
            .collect()[0]
        )
        return int(row["n"])

    def count_not_in(self, column: str, values: Iterable[Any]) -> int:
        col = self.F.col(column)
        return int(self.df.filter(col.isNotNull() & ~col.isin(list(values))).count())

    def count_outside(self, column: str, min_value: Any = None, max_value: Any = None) -> int:
        col = self.F.col(column)
        cond = self.F.lit(False)
        if min_value is not None:
            cond = cond | (col < min_value)
        if max_value is not None:
            cond = cond | (col > max_value)
        return int(self.df.filter(col.isNotNull() & cond).count())

    def max_value(self, column: str) -> Any:
        return self.df.agg(self.F.max(column).alias("m")).collect()[0]["m"]

    def sum(self, column: str) -> float:
        value = self.df.agg(self.F.sum(column).alias("s")).collect()[0]["s"]
        return float(value or 0.0)


def ops_for(df: Any) -> FrameOps:
    """Escolhe o adaptador pelo tipo do DataFrame."""
    module = type(df).__module__
    if module.startswith("pyspark"):
        return SparkOps(df)
    if module.startswith("pandas"):
        return PandasOps(df)
    raise TypeError(f"DataFrame não suportado: {type(df)!r} (use pandas ou PySpark)")
