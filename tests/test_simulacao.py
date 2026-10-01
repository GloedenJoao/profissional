import json
from datetime import date

from gestora import __main__ as cli
from gestora import armazem, config, decisoes, painel, simulacao
from gestora.mercado import Mercado

from .conftest import fake_conectores

INICIO, FIM = date(2026, 8, 3), date(2026, 9, 30)


def _rodar(fim=FIM, falhar=()):
    return cli.fechamento(fim, INICIO, conectores=fake_conectores(falhar))


def test_fundacao_e_dias_pendentes(repo):
    feitos = _rodar()
    assert feitos[0] == "2026-08-04" and feitos[-1] == "2026-09-30"
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["ultima_data"] == "2026-09-30"
    # rodar de novo no mesmo dia não reprocessa nada
    assert _rodar() == []
    p = armazem.ler_json(config.DADOS / "painel.json")
    assert p["data_referencia"] == "2026-09-30" and len(p["historico"]) == len(feitos)
    assert abs(sum(p["executivos"]["pesos"].values()) - 1) < 1e-9
    assert (config.DADOS / "briefing.md").read_text().startswith("# Briefing")


def test_deterministico(repo, tmp_path):
    _rodar()
    a = (config.DADOS / "historico.csv").read_text()
    for arq in (config.DADOS).rglob("*"):
        if arq.is_file() and arq.name != "politicas.json":
            arq.unlink()
    _rodar()
    assert (config.DADOS / "historico.csv").read_text() == a


def test_caixa_rende_cdi(repo):
    _rodar(date(2026, 8, 31))
    h = painel.ler_historico()
    assert h[-1]["bench"] > 1.0
    assert 0.9 < h[-1]["cota"] < 1.1


def test_falha_real_vira_incidente_e_resolve(repo):
    _rodar(date(2026, 9, 28))
    cli.fechamento(date(2026, 9, 29), None, conectores=fake_conectores(falhar=("yahoo",)))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    reais = [i for i in estado["incidentes"] if i["tipo"] == "falha_real" and i["estado"] == "aberto"]
    assert [i["fonte"] for i in reais] == ["yahoo"]
    assert reais[0]["id"] in estado["alertas"]
    # bova11 cai para a fonte alternativa quando a Extração liga a B3
    dec = {"data": "2026-09-30", "autor": "teste", "extracao": {"acoes": {reais[0]["id"]: "fonte_alternativa"}}}
    armazem.gravar_json(config.DECISOES / "2026-09-30.json", dec)
    assert decisoes.validar_repositorio() == []
    _rodar(date(2026, 9, 30))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    inc = next(i for i in estado["incidentes"] if i["id"] == reais[0]["id"])
    assert inc["estado"] == "resolvido"  # a fonte voltou nesta extração


def test_decisao_dos_executivos_muda_carteira(repo):
    _rodar(date(2026, 9, 29))
    aloc = {"caixa": 0.3, "prefixado": 0.2, "inflacao": 0.2, "dolar": 0.1, "bolsa": 0.2}
    armazem.gravar_json(config.DECISOES / "2026-09-30.json", {
        "data": "2026-09-30", "autor": "teste",
        "executivos": {"alocacao": aloc, "equipe_extracao": 4, "orcamento_extracao_dia": 2000,
                       "justificativa": "mais bolsa"}})
    _rodar()
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["executivos"]["alvo"] == aloc
    assert estado["extracao"]["equipe"] == 4
    pesos = simulacao._pesos(estado["fundo"]["posicoes"])
    for a, w in aloc.items():
        if a not in estado["executivos"]["congelados"]:
            assert abs(pesos[a] - w) < 0.02


def test_decisao_invalida_e_barrada(repo):
    _rodar(date(2026, 9, 29))
    armazem.gravar_json(config.DECISOES / "2026-09-30.json", {
        "data": "2026-09-30", "executivos": {"alocacao": {"caixa": 0.05, "prefixado": 0.5, "inflacao": 0.2,
                                                          "dolar": 0.1, "bolsa": 0.15}}})
    erros = decisoes.validar_repositorio()
    assert any("caixa" in e for e in erros) and any("prefixado" in e for e in erros)


def test_estrategia_suspender_congela_ativo(repo):
    _rodar(date(2026, 9, 28))
    cli.fechamento(date(2026, 9, 29), None, conectores=fake_conectores(falhar=("bcb_sgs", "bcb_ptax")))
    armazem.gravar_json(config.DECISOES / "2026-09-30.json", {
        "data": "2026-09-30", "dashboards": {"estrategias": {"dolar": "suspender"}}})
    cli.fechamento(FIM, None, conectores=fake_conectores(falhar=("bcb_sgs", "bcb_ptax")))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    dolar = estado["dashboards"]["indicadores"]["dolar"]
    assert dolar["valor"] is None and dolar["estrategia"] == "suspender"
    assert "dolar" in estado["executivos"]["congelados"]


def test_incidentes_simulados_acontecem(repo):
    _rodar()
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["seq_incidente"] > 0  # em ~2 meses a dívida técnica gera problemas


def test_politicas_do_repo_validas():
    assert decisoes.validar_politicas(json.loads(config.POLITICAS.read_text())) == []
