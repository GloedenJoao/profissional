from datetime import date

from gestora import __main__ as cli
from gestora import armazem, config, times

from .conftest import fake_conectores

INICIO = date(2026, 8, 3)


def _rodar(fim, falhar=()):
    return cli.fechamento(fim, INICIO, conectores=fake_conectores(falhar))


def _ata(d):
    return armazem.ler_json(config.DIAS / f"{d}.json")["ata"]


def test_todo_dia_tem_reuniao_das_tres_areas_em_ordem(repo):
    _rodar(date(2026, 8, 14))
    for arq in sorted(config.DIAS.glob("*.json")):
        reg = armazem.ler_json(arq)
        assert reg["decisao"]["autor"] == "times" and not reg["decisao"]["intervencao"]
        horas = [f["hora"] for f in reg["ata"]]
        assert horas == sorted(horas)
        areas = [f["area"] for f in reg["ata"]]
        assert areas.index("extracao") < areas.index("dashboards") < areas.index("executivos") < areas.index("fundo")
        assert reg["ata"][-1]["tipo"] == "fechamento"
    # sem time, sem alerta de "executivos ausentes": o comitê está lá todo dia
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert "EXEC-AUSENTE" not in estado["alertas"]


def test_comite_se_reune_toda_semana_e_decide_alocacao(repo):
    _rodar(date(2026, 8, 28))
    comites = [arq.stem for arq in sorted(config.DIAS.glob("*.json"))
               if any("Comitê de investimentos" in f["texto"] for f in _ata(arq.stem))]
    semanas = {date.fromisoformat(d).isocalendar()[1] for d in comites}
    assert len(semanas) == 4  # 04/08 a 28/08: quatro semanas, ao menos um comitê em cada
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["executivos"]["ultima_decisao"]  # algum ajuste foi feito pelos números do painel
    alvo = estado["executivos"]["alvo"]
    assert abs(sum(alvo.values()) - 1) < 1e-6
    for ativo, (mn, mx) in armazem.ler_json(config.POLITICAS)["fundo"]["limites"].items():
        assert mn - 1e-9 <= alvo[ativo] <= mx + 1e-9


def test_extracao_reage_a_falha_e_dashboards_ao_dado_faltando(repo):
    _rodar(date(2026, 9, 25))
    cli.fechamento(date(2026, 9, 28), None, conectores=fake_conectores(falhar=("bcb_sgs",)))
    cli.fechamento(date(2026, 9, 29), None, conectores=fake_conectores(falhar=("bcb_sgs",)))
    ata = _ata("2026-09-29")
    triagem = [f for f in ata if f["area"] == "extracao" and "BCB · SGS" in f["texto"]]
    assert triagem and "corrigir_conector" in triagem[0]["texto"]
    reg = armazem.ler_json(config.DIAS / "2026-09-29.json")
    assert reg["decisoes"]["dashboards"].get("cdi") == "estimar"


def test_diretriz_do_conselho_vale_por_cima_do_time(repo):
    _rodar(date(2026, 8, 28))
    armazem.gravar_json(config.DECISOES / "2026-08-31.json", {
        "data": "2026-08-31", "autor": "conselho", "executivos": {"equipe_extracao": 6}})
    _rodar(date(2026, 8, 31))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["extracao"]["equipe"] == 6
    assert any(f["tipo"] == "conselho" and "Equipe de Extração 6" in f["texto"] for f in _ata("2026-08-31"))


def test_ata_e_deterministica(repo):
    _rodar(date(2026, 8, 21))
    a = [_ata(arq.stem) for arq in sorted(config.DIAS.glob("*.json"))]
    for arq in config.DADOS.rglob("*"):
        if arq.is_file():
            arq.unlink()
    _rodar(date(2026, 8, 21))
    assert [_ata(arq.stem) for arq in sorted(config.DIAS.glob("*.json"))] == a


def test_ata_numera_horarios():
    ata = times.Ata()
    ata.diz("extracao", 0, "a")
    ata.diz("extracao", 1, "b")
    ata.diz("fundo", 0, "c")
    ata.diz("dashboards", 0, "d")
    assert [(f["hora"], f["quem"]) for f in ata.ordenada()] == [("08:00", "Bia"), ("08:02", "Téo"), ("09:00", "Caio"),
                                                                ("18:00", "Administrador")]
