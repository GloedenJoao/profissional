import json
import sqlite3

import pandas as pd
import pytest

from dq_kit import find_duplicates, profile
from dq_kit import tools
from dq_kit.cli import main as cli_main


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "voo": ["202", "202", "450", "450", "301", "999"],
            "cia": ["A", "A", "B", "B", "C", "D"],
            "status": ["no horario", "atrasado", "embarque", "embarque", "ok", "ok"],
            "portao": [1, 2, 3, 3, 4, 5],
        }
    )


def test_find_duplicates_classifies_groups(df):
    rep = find_duplicates(df, ["voo", "cia"])
    assert rep.duplicated_keys == 2 and rep.duplicated_rows == 4
    kinds = {g.key: g.kind for g in rep.groups}
    assert kinds == {("202", "A"): "divergente", ("450", "B"): "exata"}
    assert rep.column_divergence == {"status": 1, "portao": 1}
    assert rep.summary()["pct_linhas_duplicadas"] == 66.67
    assert list(rep.to_frame().columns) == ["voo", "cia", "linhas", "tipo", "colunas_divergentes"]


def test_find_duplicates_without_duplicates(df):
    rep = find_duplicates(df.drop_duplicates(["voo"]), ["voo"])
    assert rep.groups == [] and rep.summary()["por_tipo"] == {}


def test_find_duplicates_unknown_key(df):
    with pytest.raises(KeyError):
        find_duplicates(df, ["nao_existe"])


def test_profile_marks_key_candidates(df):
    cols = {c["coluna"]: c for c in profile(df)["colunas"]}
    assert cols["voo"]["candidata_a_chave"] is False
    assert cols["portao"]["maximo"] == 5
    json.dumps(profile(df))  # precisa ser serializável para o MCP


@pytest.fixture
def sqlite_path(tmp_path, df):
    path = tmp_path / "voos.db"
    with sqlite3.connect(path) as conn:
        df.to_sql("voos", conn, index=False)
    return str(path)


def test_tools_read_sqlite_and_reject_writes(sqlite_path):
    out = tools.duplicates_dataset(sqlite_path, ["voo"], table="voos")
    assert out["resumo"]["chaves_duplicadas"] == 2
    json.dumps(out)
    with pytest.raises(ValueError, match="leitura"):
        tools.profile_dataset(sqlite_path, query="DELETE FROM voos")
    with pytest.raises(ValueError, match="inválido"):
        tools.profile_dataset(sqlite_path, table="voos; DROP TABLE voos")


def test_check_dataset_verdict(sqlite_path):
    out = tools.check_dataset(sqlite_path, [{"type": "unique", "keys": ["voo"], "severity": "warn"}], table="voos")
    assert out["aprovado"] is True and out["resultados"][0]["status"] == "falhou"
    out = tools.check_dataset(sqlite_path, [{"type": "unique", "keys": ["voo"]}], table="voos")
    assert out["aprovado"] is False


def test_cli_exit_code_reflects_verdict(tmp_path, df, capsys):
    csv = tmp_path / "voos.csv"
    df.to_csv(csv, index=False)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps([{"type": "not_null", "columns": ["voo"]}]), encoding="utf-8")
    assert cli_main(["checar", str(csv), "--spec", str(spec)]) == 0
    spec.write_text(json.dumps([{"type": "unique", "keys": ["voo"]}]), encoding="utf-8")
    assert cli_main(["checar", str(csv), "--spec", str(spec)]) == 1
    assert cli_main(["duplicidades", str(csv), "--keys", "voo,cia"]) == 0
    assert '"chaves_duplicadas": 2' in capsys.readouterr().out


def test_mcp_server_registers_tools():
    pytest.importorskip("mcp")
    import asyncio

    from dq_kit.mcp_server import server

    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"perfil_dataset", "duplicidades_dataset", "checar_dataset", "resumo_controle"}
