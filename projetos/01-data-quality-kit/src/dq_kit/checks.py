"""Checks de qualidade de dados.

Cada check é um objeto chamável: recebe um DataFrame (pandas ou PySpark) e
devolve um `CheckResult` com o valor observado e o esperado — o suficiente
para gravar numa tabela de controle e entender a falha sem reabrir o código.

Os checks também podem ser montados a partir de um dicionário (`from_spec`),
o que permite declarar validações em JSON/YAML ou recebê-las de um agente de
IA via MCP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Iterable, Literal

import pandas as pd

from .frames import ops_for

Severity = Literal["error", "warn"]


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    severity: Severity
    observed: Any = None
    expected: Any = None
    detail: str = ""

    @property
    def status(self) -> str:
        return "passou" if self.passed else "falhou"


@dataclass(frozen=True)
class Check:
    name: str
    fn: Callable[[Any], tuple[bool, Any, Any, str]] = field(repr=False)
    severity: Severity = "error"

    def __call__(self, df: Any) -> CheckResult:
        try:
            passed, observed, expected, detail = self.fn(df)
        except Exception as exc:  # um check quebrado é uma falha, não um crash do pipeline
            return CheckResult(self.name, False, self.severity, None, None, f"erro ao executar: {exc}")
        return CheckResult(self.name, bool(passed), self.severity, observed, expected, detail)

    def as_warning(self) -> "Check":
        return Check(self.name, self.fn, "warn")


def _cols(columns: str | Iterable[str]) -> list[str]:
    return [columns] if isinstance(columns, str) else list(columns)


def row_count_between(min_rows: int | None = None, max_rows: int | None = None, *, severity: Severity = "error") -> Check:
    def fn(df: Any):
        n = ops_for(df).count()
        ok = (min_rows is None or n >= min_rows) and (max_rows is None or n <= max_rows)
        return ok, n, f"[{min_rows}, {max_rows}]", ""

    return Check(f"row_count_between({min_rows}, {max_rows})", fn, severity)


def row_count_equals(expected: int, *, severity: Severity = "error") -> Check:
    """Útil logo depois de um join: detecta explosão de linhas (fan-out)."""

    def fn(df: Any):
        n = ops_for(df).count()
        return n == expected, n, expected, "" if n == expected else f"diferença de {n - expected:+d} linhas"

    return Check(f"row_count_equals({expected})", fn, severity)


def not_null(columns: str | Iterable[str], *, severity: Severity = "error") -> Check:
    cols = _cols(columns)

    def fn(df: Any):
        ops = ops_for(df)
        nulls = {c: ops.null_count(c) for c in cols}
        bad = {c: n for c, n in nulls.items() if n}
        return not bad, nulls, 0, ", ".join(f"{c}: {n} nulos" for c, n in bad.items())

    return Check(f"not_null({', '.join(cols)})", fn, severity)


def unique(keys: str | Iterable[str], *, severity: Severity = "error") -> Check:
    cols = _cols(keys)

    def fn(df: Any):
        dup = ops_for(df).duplicated_row_count(cols)
        return dup == 0, dup, 0, f"{dup} linhas com chave repetida" if dup else ""

    return Check(f"unique({', '.join(cols)})", fn, severity)


def accepted_values(column: str, values: Iterable[Any], *, severity: Severity = "error") -> Check:
    allowed = list(values)

    def fn(df: Any):
        bad = ops_for(df).count_not_in(column, allowed)
        return bad == 0, bad, 0, f"{bad} valores fora de {allowed}" if bad else ""

    return Check(f"accepted_values({column})", fn, severity)


def values_between(column: str, min_value: Any = None, max_value: Any = None, *, severity: Severity = "error") -> Check:
    def fn(df: Any):
        bad = ops_for(df).count_outside(column, min_value, max_value)
        return bad == 0, bad, 0, f"{bad} valores fora de [{min_value}, {max_value}]" if bad else ""

    return Check(f"values_between({column}, {min_value}, {max_value})", fn, severity)


def freshness(column: str, max_age: timedelta, *, now: datetime | None = None, severity: Severity = "error") -> Check:
    """A data mais recente da coluna não pode ser mais velha que `max_age`."""

    def fn(df: Any):
        latest = ops_for(df).max_value(column)
        if latest is None:
            return False, None, f"<= {max_age}", "coluna sem valores"
        latest_ts = pd.Timestamp(latest).to_pydatetime()
        reference = now or datetime.now()
        age = reference - latest_ts
        return age <= max_age, str(latest_ts), f"idade <= {max_age}", f"idade {age}"

    return Check(f"freshness({column}, {max_age})", fn, severity)


def sum_matches(column: str, expected_total: float, *, tolerance: float = 0.0, severity: Severity = "error") -> Check:
    """Reconciliação: soma de uma coluna bate com um total de referência."""

    def fn(df: Any):
        total = ops_for(df).sum(column)
        diff = total - expected_total
        return abs(diff) <= tolerance, round(total, 6), expected_total, f"diferença {diff:+.2f}" if diff else ""

    return Check(f"sum_matches({column})", fn, severity)


def custom(name: str, predicate: Callable[[Any], bool], *, severity: Severity = "error") -> Check:
    return Check(name, lambda df: (predicate(df), None, True, ""), severity)


_BUILDERS: dict[str, Callable[..., Check]] = {
    "row_count_between": row_count_between,
    "row_count_equals": row_count_equals,
    "not_null": not_null,
    "unique": unique,
    "accepted_values": accepted_values,
    "values_between": values_between,
    "sum_matches": sum_matches,
}


def from_spec(spec: dict[str, Any]) -> Check:
    """Monta um check a partir de um dicionário, ex.:

    {"type": "unique", "keys": ["cnpj"]}
    {"type": "values_between", "column": "valor", "min_value": 0, "severity": "warn"}
    {"type": "freshness", "column": "dt_ref", "max_age_days": 2}
    """
    spec = dict(spec)
    kind = spec.pop("type", None)
    if kind == "freshness":
        spec["max_age"] = timedelta(days=spec.pop("max_age_days"))
        return freshness(**spec)
    if kind not in _BUILDERS:
        raise ValueError(f"tipo de check desconhecido: {kind!r}. Opções: {sorted([*_BUILDERS, 'freshness'])}")
    return _BUILDERS[kind](**spec)


def run_checks(df: Any, checks: Iterable[Check]) -> list[CheckResult]:
    return [check(df) for check in checks]
