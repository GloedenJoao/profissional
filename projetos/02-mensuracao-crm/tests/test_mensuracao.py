import sqlite3

import pytest

from mensuracao import analise
from mensuracao.__main__ import main
from mensuracao.simulacao import SCHEMA, CANAIS, Parametros, gerar


@pytest.fixture
def conn_manual():
    """Base mínima montada à mão, onde a resposta certa é conhecida."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO canais VALUES (?,?,?)", CANAIS)
    conn.execute("INSERT INTO campanhas VALUES (1, 'teste', 'crm', '2026-07-01', '2026-07-07')")
    return conn


def test_last_touch_rules(conn_manual):
    c = conn_manual
    c.executemany(
        "INSERT INTO toques VALUES (?,?,?)",
        [
            (1, "midia_paga", "2026-07-02"), (1, "crm", "2026-07-05"),        # último toque = crm
            (2, "crm", "2026-07-03"), (2, "gerente", "2026-07-03"),          # empate no dia → gerente (prioridade 1)
            (3, "crm", "2026-07-20"),                                         # toque DEPOIS da conversão → ignora
            (4, "mgm", "2026-05-01"),                                         # fora do lookback de 30 dias → ignora
        ],
    )
    c.executemany(
        "INSERT INTO conversoes VALUES (?,?,?)",
        [(1, "2026-07-10", "x"), (2, "2026-07-10", "x"), (3, "2026-07-10", "x"), (4, "2026-07-10", "x"),
         (5, "2026-09-01", "x")],  # fora do período analisado
    )
    resumo = analise.atribuir_last_touch(c, "2026-07-01", "2026-08-06", lookback=30)
    detalhe = {r[0]: r[1] for r in c.execute("SELECT cliente_id, canal_atribuido FROM last_touch")}
    assert detalhe == {1: "crm", 2: "gerente", 3: "organico", 4: "organico"}
    assert {r["canal"]: r["conversoes"] for r in resumo} == {"organico": 2, "crm": 1, "gerente": 1}
    assert sum(r["pct_total"] for r in resumo) == pytest.approx(100)


def test_lift_counts_each_client_once_and_respects_window(conn_manual):
    c = conn_manual
    c.executemany("INSERT INTO publico_campanha VALUES (1, ?, ?)",
                  [(1, "tratamento"), (2, "tratamento"), (3, "controle"), (4, "controle")])
    c.executemany(
        "INSERT INTO conversoes VALUES (?,?,?)",
        [(1, "2026-07-03", "a"), (1, "2026-07-04", "b"),   # duas conversões, um cliente
         (3, "2026-06-20", "a"),                           # antes da campanha
         (4, "2026-08-30", "a")],                          # depois da janela (07-07 + 30d)
    )
    lift = analise.medir_lift(c, 1, janela=30)
    assert (lift.n_tratamento, lift.conv_tratamento, lift.n_controle, lift.conv_controle) == (2, 1, 2, 0)


def test_stats_against_known_values():
    lift = analise.Lift(n_tratamento=10_000, conv_tratamento=600, n_controle=10_000, conv_controle=500)
    assert lift.lift_abs == pytest.approx(0.01)
    assert lift.lift_rel == pytest.approx(0.2)
    assert lift.z == pytest.approx(3.10, abs=0.01)
    assert lift.p_valor == pytest.approx(0.0019, abs=0.0002)
    lo, hi = lift.ic95
    assert lo < 0.01 < hi and hi - lo == pytest.approx(2 * 1.96 * lift.erro_padrao, rel=1e-3)
    assert lift.conversoes_incrementais == pytest.approx(100)


def test_mde_and_holdout_sizing():
    # base 4%, 10k x 10k → MDE ≈ 0.78 p.p.
    assert analise.efeito_minimo_detectavel(10_000, 10_000, 0.04) == pytest.approx(0.00776, abs=1e-4)
    pct = analise.holdout_necessario(20_000, 0.044, 0.01)
    assert 0.15 < pct < 0.30
    assert analise.holdout_necessario(1_000, 0.04, 0.001) is None


def test_simulation_recovers_true_lift(tmp_path):
    p = Parametros(n_clientes=60_000, pct_controle=0.5, seed=1)
    with sqlite3.connect(gerar(tmp_path / "b.db", p)) as conn:
        lift = analise.medir_lift(conn, 1, p.janela_dias)
    lo, hi = lift.ic95
    assert lo <= p.lift_real <= hi
    assert lift.lift_abs == pytest.approx(p.lift_real, abs=0.004)


def test_simulation_is_deterministic(tmp_path):
    def snapshot(path):
        with sqlite3.connect(path) as conn:
            return conn.execute("SELECT COUNT(*), SUM(cliente_id) FROM conversoes").fetchone()

    p = Parametros(n_clientes=2_000)
    assert snapshot(gerar(tmp_path / "a.db", p)) == snapshot(gerar(tmp_path / "b.db", p))


def test_cumulative_curve_is_monotonic(tmp_path):
    p = Parametros(n_clientes=3_000)
    with sqlite3.connect(gerar(tmp_path / "c.db", p)) as conn:
        curva = analise.curva_acumulada(conn, 1, 30)
    for grupo in ("tratamento", "controle"):
        serie = [r["acumuladas"] for r in curva if r["grupo"] == grupo]
        assert len(serie) == 31 and serie == sorted(serie)
    assert analise.grafico_svg(curva).startswith("<svg")


def test_end_to_end_report(tmp_path, capsys):
    saida = main(["--saida", str(tmp_path / "rel")])
    texto = (saida / "relatorio.md").read_text(encoding="utf-8")
    assert "superestima o CRM" in texto and "Poder do desenho" in texto
    assert (saida / "curva_acumulada.svg").exists()
