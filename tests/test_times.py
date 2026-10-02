from datetime import date

import pytest

from gestora import __main__ as cli
from gestora import armazem, config, simulacao, times
from gestora.rastro import Rastro

from .conftest import fake_conectores

INICIO = date(2026, 8, 3)
ORDEM = ["heranca", "extracao", "dashboards", "comite", "fundo", "empresa", "verificacoes"]


def _rodar(fim, falhar=()):
    return cli.fechamento(fim, INICIO, conectores=fake_conectores(falhar))


def _dia(d):
    return armazem.ler_json(config.DIAS / f"{d}.json")


def test_todo_dia_passa_pelas_sete_etapas_e_toda_fala_tem_conta(repo):
    _rodar(date(2026, 8, 14))
    for arq in sorted(config.DIAS.glob("*.json")):
        reg = armazem.ler_json(arq)
        assert [e["id"] for e in reg["rastro"]] == ORDEM
        assert reg["decisao"]["autor"] == "times" and not reg["decisao"]["intervencao"]
        horas = [f["hora"] for f in reg["ata"]]
        assert horas == sorted(horas)
        blocos = {b["id"] for e in reg["rastro"] for b in e["blocos"]}
        for f in reg["ata"]:
            assert f["etapa"] in ORDEM
            assert f["bloco"] is None or f["bloco"] in blocos, f"fala sem conta: {f['texto']}"
        com_conta = [f for f in reg["ata"] if f["bloco"]]
        assert len(com_conta) >= len(reg["ata"]) - 1  # só a abertura da Extração pode não ter tabela
        assert reg["ata"][-1]["tipo"] == "fechamento"
        assert all(c["ok"] for c in reg["verificacoes"]), reg["verificacoes"]


def test_comite_se_reune_no_primeiro_dia_util_da_semana(repo):
    _rodar(date(2026, 8, 28))
    reunioes = [arq.stem for arq in sorted(config.DIAS.glob("*.json"))
                if any("Reunião de investimentos hoje" in f["texto"] for f in _dia(arq.stem)["ata"])]
    semanas = {date.fromisoformat(d).isocalendar()[1] for d in reunioes}
    assert len(semanas) == 4  # 04/08 a 28/08: quatro semanas, ao menos uma reunião em cada
    assert "2026-08-10" in reunioes and "2026-08-17" in reunioes  # segundas-feiras
    estado = armazem.ler_json(config.DADOS / "estado.json")
    alvo = estado["executivos"]["alvo"]
    assert abs(sum(alvo.values()) - 1) < 1e-6
    for ativo, (mn, mx) in armazem.ler_json(config.POLITICAS)["fundo"]["limites"].items():
        assert mn - 1e-9 <= alvo[ativo] <= mx + 1e-9


def test_extracao_reage_a_falha_e_dashboards_ao_dado_faltando(repo):
    _rodar(date(2026, 9, 25))
    cli.fechamento(date(2026, 9, 28), None, conectores=fake_conectores(falhar=("bcb_sgs",)))
    cli.fechamento(date(2026, 9, 29), None, conectores=fake_conectores(falhar=("bcb_sgs",)))
    ata = _dia("2026-09-29")["ata"]
    triagem = [f for f in ata if f["etapa"] == "extracao" and "BCB · SGS" in f["texto"] and "`" in f["texto"]]
    assert triagem and "corrigir_conector" in triagem[0]["texto"]
    reg = _dia("2026-09-29")
    assert reg["decisoes"]["dashboards"].get("cdi") == "estimar"
    cdi = next(b for e in reg["rastro"] if e["id"] == "dashboards" for b in e["blocos"] if b["titulo"].startswith("Painel"))
    linha = next(ln for ln in cdi["linhas"] if ln[0].startswith("CDI"))
    assert "Selic" in linha[5]["v"]  # a conta da estimativa aparece no painel


def test_diretriz_do_conselho_vale_por_cima_do_time(repo):
    _rodar(date(2026, 8, 28))
    armazem.gravar_json(config.DECISOES / "2026-08-31.json", {
        "data": "2026-08-31", "autor": "conselho", "executivos": {"equipe_extracao": 6}})
    _rodar(date(2026, 8, 31))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["extracao"]["equipe"] == 6
    assert any(f["tipo"] == "conselho" and "Equipe de Extração 6" in f["texto"] for f in _dia("2026-08-31")["ata"])


def test_ata_e_rastro_sao_deterministicos(repo):
    _rodar(date(2026, 8, 21))
    a = [_dia(arq.stem) for arq in sorted(config.DIAS.glob("*.json"))]
    for arq in config.DADOS.rglob("*"):
        if arq.is_file():
            arq.unlink()
    _rodar(date(2026, 8, 21))
    assert [_dia(arq.stem) for arq in sorted(config.DIAS.glob("*.json"))] == a


@pytest.mark.parametrize("tipo,dias,alt,esperado", [
    ("falha_real", 1, False, "corrigir_conector"),
    ("mudanca_formato", 1, True, "corrigir_conector"),
    ("fora_do_ar", 1, True, "fonte_alternativa"),
    ("fora_do_ar", 1, False, "aguardar"),
    ("fora_do_ar", 2, False, "corrigir_conector"),
    ("fora_do_ar", 4, True, "corrigir_conector"),
    ("atraso", 1, True, "aguardar"),
    ("atraso", 2, True, "fonte_alternativa"),
    ("atraso", 3, False, "corrigir_conector"),
    ("atraso", 5, True, "corrigir_conector"),
])
def test_regras_da_triagem(tipo, dias, alt, esperado):
    assert times._regra_incidente(tipo, dias, alt)[0] == esperado


def _estado_com_painel(valores: dict, confianca: float = 1.0, alvo: dict | None = None) -> dict:
    politicas = armazem.ler_json(config.POLITICAS)
    estado = {"executivos": {"alvo": dict(alvo or politicas["fundo"]["alocacao_inicial"])},
              "dashboards": {"indicadores": {}}}
    for ind, v in valores.items():
        reg = {"valor": v, "confianca": confianca}
        if ind in ("bova11", "dolar"):
            reg = {"valor": 1.0, "confianca": confianca,
                   "tendencia": {"valor": v, "de": "2026-01-01", "ate": "2026-01-30", "n": 20}}
        estado["dashboards"]["indicadores"][ind] = reg
    return estado, politicas


def test_modelo_de_alocacao_conta_e_travas(repo):
    ctx = {"congelados": [], "defensivo": False}
    # prefixado paga 1 p.p. acima do Focus: sinal +0,5 → 15% + 10 p.p. × 0,5 = 20%
    # IPCA+ a 9,5% real: sinal (9,5 − 5,5)/2 = +2 → limitado a +1 → desejado 25%, mas o passo máximo é 5 p.p. → 20%
    # bolsa +1% em 20 pregões: sinal +0,125 → 16,25%: mudança menor que 2 p.p., fica em 15%
    estado, pol = _estado_com_painel({"taxa_pre": 13.5, "focus_selic": 12.5, "taxa_ipca": 9.5, "bova11": 0.01,
                                      "dolar": 0.0})
    novo, linhas, desfecho = times.alocacao(estado, pol, ctx)
    assert novo["prefixado"] == pytest.approx(0.20)
    assert novo["inflacao"] == pytest.approx(0.20) and "passo máximo" in desfecho["inflacao"]["trava"]
    assert novo["bolsa"] == pytest.approx(0.15) and "menor que 2 p.p." in desfecho["bolsa"]["trava"]
    assert novo["dolar"] == pytest.approx(0.10)
    assert sum(novo.values()) == pytest.approx(1.0)
    assert novo["caixa"] == pytest.approx(0.35)
    # número com confiança baixa não mexe a carteira
    estado, pol = _estado_com_painel({"taxa_pre": 13.5, "focus_selic": 12.5, "taxa_ipca": 9.5}, confianca=0.4)
    novo, _, desfecho = times.alocacao(estado, pol, ctx)
    assert novo == pol["fundo"]["alocacao_inicial"] | {"caixa": novo["caixa"]}
    assert "confiança 40%" in desfecho["prefixado"]["trava"]
    # na defensiva, bolsa não sobe
    estado, pol = _estado_com_painel({"bova11": 0.08})
    novo, _, desfecho = times.alocacao(estado, pol, {"congelados": [], "defensivo": True})
    assert novo["bolsa"] == pytest.approx(0.15) and "defensiva" in desfecho["bolsa"]["trava"]


def test_rastro_numera_falas_por_etapa():
    r = Rastro()
    e = r.etapa("extracao", "extracao", "08:00", "Extração", "?")
    e.diz(0, "a")
    e.diz(1, "b", minutos=10)
    f = r.etapa("fundo", "fundo", "18:00", "Fundo", "?")
    f.diz(0, "c")
    d = r.etapa("dashboards", "dashboards", "09:00", "Dashboards", "?")
    d.diz(0, "d")
    assert [(x["hora"], x["quem"]) for x in r.ata()] == [("08:00", "Bia"), ("08:10", "Téo"), ("09:00", "Caio"),
                                                        ("18:00", "Administrador")]


def test_sem_estresse_so_falha_real_abre_incidente(repo):
    pol = armazem.ler_json(config.POLITICAS)
    pol["extracao"]["estresse"] = {"ativo": False, "multiplicador": 1.0}
    armazem.gravar_json(config.POLITICAS, pol)
    _rodar(date(2026, 9, 30))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["metricas"]["incidentes_simulados"] == 0
    reg = _dia("2026-09-30")
    estresse = next(b for e in reg["rastro"] if e["id"] == "extracao" for b in e["blocos"] if "estresse" in b["titulo"])
    assert all("desligado" in str(ln[3]) for ln in estresse["linhas"])
    assert simulacao.VERSAO_MOTOR == estado["versao"]
