from datetime import datetime, timedelta

import pandas as pd
import pytest

from dq_kit import checks as C


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 3],
            "canal": ["crm", "midia", "crm", "outro"],
            "valor": [10.0, -5.0, 20.0, None],
            "dt": pd.to_datetime(["2026-09-01", "2026-09-10", "2026-09-28", "2026-09-29"]),
        }
    )


def test_row_count(df):
    assert C.row_count_between(1, 10)(df).passed
    assert not C.row_count_between(min_rows=5)(df).passed
    res = C.row_count_equals(3)(df)
    assert not res.passed and res.observed == 4 and "+1" in res.detail


def test_not_null_reports_per_column(df):
    res = C.not_null(["id", "valor"])(df)
    assert not res.passed
    assert res.observed == {"id": 0, "valor": 1}
    assert "valor: 1 nulos" in res.detail


def test_unique_counts_all_rows_of_repeated_keys(df):
    res = C.unique("id")(df)
    assert not res.passed and res.observed == 2
    assert C.unique(["id", "canal"])(df).passed


def test_accepted_values_and_between_ignore_nulls(df):
    assert C.accepted_values("canal", ["crm", "midia"])(df).observed == 1
    res = C.values_between("valor", min_value=0)(df)
    assert res.observed == 1  # o -5; o nulo não conta


def test_freshness(df):
    now = datetime(2026, 9, 30)
    assert C.freshness("dt", timedelta(days=2), now=now)(df).passed
    assert not C.freshness("dt", timedelta(hours=12), now=now)(df).passed


def test_sum_matches_with_tolerance(df):
    assert C.sum_matches("valor", 25.0)(df).passed
    assert not C.sum_matches("valor", 26.0)(df).passed
    assert C.sum_matches("valor", 26.0, tolerance=1.0)(df).passed


def test_broken_check_is_a_failure_not_a_crash(df):
    res = C.not_null("coluna_que_nao_existe")(df)
    assert not res.passed and "erro ao executar" in res.detail


def test_as_warning_keeps_logic(df):
    res = C.unique("id").as_warning()(df)
    assert not res.passed and res.severity == "warn"


def test_from_spec_builds_equivalent_checks(df):
    assert C.from_spec({"type": "unique", "keys": ["id"]})(df).observed == 2
    assert C.from_spec({"type": "values_between", "column": "valor", "min_value": 0, "severity": "warn"})(df).severity == "warn"
    fresh = C.from_spec({"type": "freshness", "column": "dt", "max_age_days": 3, "now": datetime(2026, 9, 30)})
    assert fresh(df).passed
    with pytest.raises(ValueError, match="desconhecido"):
        C.from_spec({"type": "nao_existe"})
