"""Os mesmos checks, rodando em PySpark. Pulado se pyspark/Java não estiverem disponíveis."""

import pandas as pd
import pytest

pyspark = pytest.importorskip("pyspark")

from dq_kit import Pipeline, ValidationError, checks as C  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    from pyspark.sql import SparkSession

    try:
        session = SparkSession.builder.master("local[1]").appName("dq-kit-tests").getOrCreate()
    except Exception as exc:  # sem Java na máquina
        pytest.skip(f"Spark indisponível: {exc}")
    yield session
    session.stop()


@pytest.fixture
def pdf():
    return pd.DataFrame({"id": [1, 2, 3, 3], "canal": ["crm", "midia", "crm", "outro"], "valor": [10.0, -5.0, 20.0, None]})


@pytest.mark.parametrize(
    "check",
    [
        C.row_count_between(1, 10),
        C.row_count_equals(3),
        C.not_null(["id", "valor"]),
        C.unique("id"),
        C.unique(["id", "canal"]),
        C.accepted_values("canal", ["crm", "midia"]),
        C.values_between("valor", min_value=0),
        C.sum_matches("valor", 25.0),
    ],
    ids=lambda c: c.name,
)
def test_spark_and_pandas_agree(spark, pdf, check):
    rows = [tuple(None if pd.isna(v) else v for v in r) for r in pdf.itertuples(index=False)]
    sdf = spark.createDataFrame(rows, "id long, canal string, valor double")
    on_pandas, on_spark = check(pdf), check(sdf)
    assert (on_spark.passed, on_spark.observed) == (on_pandas.passed, on_pandas.observed)


def test_pipeline_runs_on_spark(spark):
    leads = spark.createDataFrame([(1,), (2,), (3,)], ["k"])
    contas = spark.createDataFrame([(1, "a"), (1, "b"), (2, "c")], ["k", "v"])

    def transform(ctx, leads, contas):
        joined = leads.join(contas, "k", "left")
        ctx.checkpoint("joined", joined, [C.row_count_equals(leads.count())])
        return joined

    with pytest.raises(ValidationError) as exc:
        Pipeline("spark").step("join", inputs={"leads": leads, "contas": contas}, transform=transform)
    assert exc.value.failures[0].observed == 4
