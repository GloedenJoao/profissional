from datetime import datetime

import pandas as pd
import pytest

from dq_kit import ControlTable, Pipeline, ValidationError, checks as C, hive_ddl

FIXED = datetime(2026, 9, 30, 8, 0)


def make_pipeline(ct=None):
    return Pipeline("teste", ct, run_id="run1", clock=lambda: FIXED)


def identity(ctx, df):
    return df


def test_pre_failure_blocks_transform():
    called = []

    def transform(ctx, df):
        called.append(True)
        return df

    p = make_pipeline()
    with pytest.raises(ValidationError) as exc:
        p.step("s", inputs={"df": pd.DataFrame({"id": [1, 1]})}, transform=transform, pre={"df": [C.unique("id")]})
    assert exc.value.layer == "pre"
    assert called == []


def test_all_checks_in_a_layer_run_before_raising():
    p = make_pipeline()
    df = pd.DataFrame({"id": [1, 1, None]})
    with pytest.raises(ValidationError) as exc:
        p.step("s", inputs={"df": df}, transform=identity,
               pre={"df": [C.unique("id"), C.not_null("id"), C.row_count_between(1)]})
    assert len(exc.value.failures) == 2
    assert len(p.records) == 3


def test_checkpoint_catches_join_fanout():
    left = pd.DataFrame({"k": [1, 2, 3]})
    right = pd.DataFrame({"k": [1, 1, 2], "v": ["a", "b", "c"]})

    def transform(ctx, left, right):
        joined = left.merge(right, on="k", how="left")
        ctx.checkpoint("joined", joined, [C.row_count_equals(len(left))])
        return joined

    p = make_pipeline()
    with pytest.raises(ValidationError) as exc:
        p.step("join", inputs={"left": left, "right": right}, transform=transform)
    assert exc.value.layer == "durante"
    assert exc.value.failures[0].observed == 4


def test_warnings_are_logged_but_do_not_block():
    p = make_pipeline()
    out = p.step("s", inputs={"df": pd.DataFrame({"v": [-1, 2]})}, transform=identity,
                 post=[C.values_between("v", min_value=0).as_warning()])
    assert len(out) == 2
    assert p.records[0].result.status == "falhou"
    assert "[WRN]" in p.report()


def test_pre_check_for_unknown_input_is_a_programming_error():
    with pytest.raises(KeyError):
        make_pipeline().step("s", inputs={"df": pd.DataFrame()}, transform=identity, pre={"outro": []})


def test_control_table_persists_every_result(tmp_path):
    ct = ControlTable(tmp_path / "ctl.db")
    p = make_pipeline(ct)
    p.step("s", inputs={"df": pd.DataFrame({"id": [1, 2]})}, transform=identity,
           pre={"df": [C.unique("id")]}, post=[C.row_count_equals(2)], output_name="saida")
    rows = ct.rows("run1")
    assert [(r["layer"], r["dataset"], r["status"]) for r in rows] == [("pre", "df", "passou"), ("pos", "saida", "passou")]
    assert rows[0]["executed_at"] == "2026-09-30T08:00:00"
    assert ct.summary() == [
        {"run_id": "run1", "pipeline": "teste", "layer": "pre", "passou": 1, "falhou_erro": 0, "falhou_alerta": 0},
        {"run_id": "run1", "pipeline": "teste", "layer": "pos", "passou": 1, "falhou_erro": 0, "falhou_alerta": 0},
    ]


def test_hive_ddl_is_partitioned():
    ddl = hive_ddl()
    assert "PARTITIONED BY (dt_execucao STRING)" in ddl and "STORED AS PARQUET" in ddl


def test_example_pipeline_runs_end_to_end(tmp_path, capsys):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "examples" / "pipeline_aquisicao_pj.py"
    spec = importlib.util.spec_from_file_location("exemplo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(tmp_path / "ctl.db")
    out = capsys.readouterr().out
    assert "execução interrompida antes de gravar" in out
    assert "'divergente': 4" in out
    assert "'segmento': 4" in out
