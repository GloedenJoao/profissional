import json
from datetime import date

import pytest

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


def test_verificacoes_passam_em_dois_meses(repo):
    _rodar()
    assert cli.auditar() == []
    p = armazem.ler_json(config.DADOS / "painel.json")
    assert {c["id"] for c in p["verificacoes"]} == {"sem_futuro", "portao", "contabilidade", "reconciliacao", "limites",
                                                    "precos", "caixa_gestora", "referencia"}
    assert all(c["falhas"] == 0 for c in p["verificacoes"])
    # o painel antigo continua igual para quem já lia (app Android), com os campos novos ao lado
    for chave in ("resumo", "extracao", "dashboards", "executivos", "alertas", "dias", "historico", "ata", "nomes"):
        assert chave in p
    for chave in ("calendario", "regras", "fundacao", "referencia", "metricas", "series", "versao_motor"):
        assert chave in p


def test_reunioes_so_veem_o_que_estava_publicado_as_8h(repo):
    _rodar(date(2026, 9, 16))
    reg = armazem.ler_json(config.DIAS / "2026-09-16.json")
    estado = armazem.ler_json(config.DADOS / "estado.json")
    ind = estado["dashboards"]["indicadores"]
    assert ind["cdi"]["data_ref"] == "2026-09-15"  # o CDI de hoje só sai depois das reuniões
    assert ind["bova11"]["data_ref"] <= "2026-09-15"
    assert ind["ipca_12m"]["data_ref"] == "2026-08-01"  # dia 16: o IPCA de agosto já saiu, o de setembro não
    assert ind["focus_selic"]["data_ref"] == "2026-09-11"  # Focus de segunda traz a pesquisa até sexta
    # a marcação do fundo, às 18h, usa o fechamento do próprio dia
    assert estado["fundo"]["posicoes"]["bolsa"]["data_preco"] == "2026-09-16"
    assert next(c for c in reg["verificacoes"] if c["id"] == "sem_futuro")["ok"]


def test_ipca_antes_do_dia_15_ainda_e_o_de_dois_meses_antes(repo):
    _rodar(date(2026, 9, 14))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["dashboards"]["indicadores"]["ipca_12m"]["data_ref"] == "2026-07-01"


def test_fluxo_de_cotistas_segue_o_modelo_sem_sorteio(repo):
    _rodar(date(2026, 8, 20))
    reg = armazem.ler_json(config.DIAS / "2026-08-20.json")
    fundo = next(e for e in reg["rastro"] if e["id"] == "fundo")
    contas = next(b for b in fundo["blocos"] if b["titulo"].startswith("Aplicações"))
    assert [ln["rot"] for ln in contas["linhas"]] == ["captação de base", "desempenho", "credibilidade", "fluxo do dia"]
    assert "semente" not in str(contas["linhas"])


def test_sem_comite_fundo_anda_com_a_referencia(repo):
    pol = armazem.ler_json(config.POLITICAS)
    pol["executivos"]["modelo"]["sensibilidade"] = {"prefixado": 0, "inflacao": 0, "dolar": 0, "bolsa": 0}
    pol["fundo"]["cotistas"] |= {"captacao_base": 0, "sens_desempenho": 0, "sens_credibilidade": 0}
    armazem.gravar_json(config.POLITICAS, pol)
    _rodar()
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["metricas"]["mudancas_alvo"] == 0
    # sem decisões e sem cotistas, o fundo é a carteira de referência
    assert estado["fundo"]["cota"] == pytest.approx(estado["referencia"]["cota"], rel=1e-9)


def test_motor_novo_reprocessa_o_historico(repo):
    _rodar(date(2026, 8, 31))
    antes = (config.DADOS / "historico.csv").read_text()
    estado = armazem.ler_json(config.DADOS / "estado.json")
    estado["versao"] = 1
    armazem.gravar_json(config.DADOS / "estado.json", estado)
    assert cli.precisa_reprocessar()
    cli.fechamento(date(2026, 9, 1), None, extrair=False)
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["versao"] == simulacao.VERSAO_MOTOR and estado["ultima_data"] == "2026-09-01"
    depois = (config.DADOS / "historico.csv").read_text().splitlines()
    assert depois[:-1] == antes.splitlines()  # o mesmo motor refaz o mesmo passado, e o dia novo entra no fim
    assert depois[-1].startswith("2026-09-01")
