import json
import shutil
from datetime import date

import pytest

from gestora import __main__ as cli
from gestora import armazem, comandos, config, simulacao

from .conftest import fake_conectores

HOJE = date(2026, 10, 2)
GLOBAIS = ("RAIZ", "CENARIOS", "CENARIO", "SEMENTE", "DADOS", "SERIES", "DIAS", "EMPRESA", "DECISOES", "DIARIO",
           "POLITICAS")


@pytest.fixture
def raiz(tmp_path):
    """Repositório de mentira com um cenário paralelo `teste`; restaura os caminhos globais no fim."""
    antes = {k: getattr(config, k) for k in GLOBAIS}
    (tmp_path / "empresa" / "decisoes").mkdir(parents=True)
    shutil.copy(config.POLITICAS, tmp_path / "empresa" / "politicas.json")
    shutil.copytree(config.RAIZ / "site", tmp_path / "site")
    cen = tmp_path / "cenarios" / "teste"
    (cen / "empresa" / "decisoes").mkdir(parents=True)
    shutil.copy(config.POLITICAS, cen / "empresa" / "politicas.json")
    armazem.gravar_json(cen / "cenario.json", {"nome": "Teste", "descricao": "d", "inicio": "2026-08-03"})
    config.RAIZ, config.CENARIOS = tmp_path, tmp_path / "cenarios"
    config.usar_cenario("ao-vivo")
    yield tmp_path
    for k, v in antes.items():
        setattr(config, k, v)


def _avancar(**kw):
    return cli.avancar(conectores=fake_conectores(), hoje=HOJE, **kw)


def test_cenario_tem_pastas_proprias(raiz):
    meta = config.usar_cenario("teste")
    assert meta["modo"] == "simulacao" and config.DADOS == raiz / "cenarios" / "teste" / "dados"
    assert config.SEMENTE == "teste"
    config.usar_cenario("ao-vivo")
    assert config.DADOS == raiz / "dados" and config.SEMENTE == ""
    with pytest.raises(SystemExit):
        config.usar_cenario("nao-existe")


def test_avancar_funda_e_anda_em_blocos(raiz):
    config.usar_cenario("teste")
    assert _avancar(dias=1) == ["2026-08-04"]
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["inicio"] == "2026-08-03" and estado["ultima_data"] == "2026-08-04"
    assert not (raiz / "dados" / "estado.json").exists()  # o ao vivo não foi tocado
    feitos = _avancar(dias=20)  # dois blocos de extração
    assert len(feitos) == 20 and feitos[0] == "2026-08-05"
    # nunca passa de ontem
    feitos = _avancar(ate=date(2027, 1, 1))
    assert feitos[-1] == "2026-10-01"
    assert _avancar(dias=1) == []


def test_semente_do_cenario_muda_o_acaso():
    d = date(2026, 3, 2)
    antes = config.SEMENTE
    try:
        config.SEMENTE = ""
        a = simulacao.rng(d, "x").random()
        config.SEMENTE = "2026"
        b = simulacao.rng(d, "x").random()
    finally:
        config.SEMENTE = antes
    assert a != b


def test_painel_traz_status_ata_e_diretriz_opcional(raiz):
    config.usar_cenario("teste")
    _avancar(dias=3)
    p = armazem.ler_json(config.DADOS / "painel.json")
    assert p["cenario"]["id"] == "teste" and p["proximo_fechamento_em"] is None
    assert set(p["status_areas"]) == {"extracao", "dashboards", "executivos", "fundo"}
    assert p["datas"] == ["2026-08-04", "2026-08-05", "2026-08-06"]
    assert p["ata"] and {f["area"] for f in p["ata"]} >= {"extracao", "dashboards", "executivos", "fundo"}
    # ninguém precisa escrever decisão: os times decidem
    assert not any(t["id"] in ("DECISAO", "DIRETRIZ") for t in p["tarefas"])
    dec = p["decisao_proxima"]
    assert dec["caminho"] == "cenarios/teste/empresa/decisoes/2026-08-07.json" and not dec["existe"]
    assert "new/main/cenarios/teste/empresa/decisoes?filename=2026-08-07.json" in dec["link_criar"]
    # a diretriz pronta é válida: salva, vale por cima dos times no próximo avanço e entra na ata
    modelo = dec["modelo"] | {"executivos": dec["modelo"]["executivos"] | {"justificativa": "teste"}}
    armazem.gravar_json(config.DECISOES / "2026-08-07.json", modelo)
    assert cli.main(["--cenario", "teste", "validar"]) == 0
    cli.gerar_painel()
    p = armazem.ler_json(config.DADOS / "painel.json")
    assert p["decisao_proxima"]["existe"] and any(t["id"] == "DIRETRIZ" for t in p["tarefas"])
    _avancar(dias=1)
    reg = armazem.ler_json(config.DIAS / "2026-08-07.json")
    assert reg["decisao"] == {"existe": True, "autor": "conselho + times", "intervencao": True}
    assert any(f["tipo"] == "conselho" for f in reg["ata"])
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["executivos"]["alvo"] == modelo["executivos"]["alocacao"]


def test_resumo_do_avanco(raiz, tmp_path):
    config.usar_cenario("teste")
    feitos = _avancar(dias=2)
    texto = cli.resumo_avanco(feitos)
    assert texto.startswith("### Teste: 2026-08-04 → 2026-08-05 (2 dia(s)")
    assert "O que os times decidiram" in texto and "#/teste/aovivo" in texto


def test_site_reune_os_paineis(raiz):
    config.usar_cenario("teste")
    _avancar(dias=1)
    indice = cli.montar_site(raiz / "_site")
    assert [c["id"] for c in indice] == ["ao-vivo", "teste"]
    assert indice[0]["painel"] is None and indice[1]["painel"] == "cenarios/teste/painel.json"
    assert (raiz / "_site" / "cenarios" / "teste" / "painel.json").exists()
    assert (raiz / "_site" / "cenarios" / "teste" / "dias" / "2026-08-04.json").exists()
    versao = json.loads((raiz / "_site" / "versao.json").read_text())
    assert versao["paineis"] == {"teste": "2026-08-04"}
    pagina = (raiz / "_site" / "index.html").read_text()
    assert "__VERSAO__" not in pagina and f"app.js?v={versao['codigo']}" in pagina
    assert f'window.VERSAO = "{versao["versao"]}"' in pagina
    assert json.loads((raiz / "_site" / "cenarios.json").read_text())["cenarios"][1]["modo"] == "simulacao"
    assert (raiz / "_site" / "index.html").exists()


@pytest.mark.parametrize("texto,esperado", [
    ("/avancar", {"dias": 1}),
    ("/avancar 5", {"dias": 5}),
    ("/Avançar 12\nobrigado", {"dias": 12}),
    ("/avancar ate 2026-03-31", {"ate": "2026-03-31"}),
    ("/avancar até 31/03/2026", {"ate": "2026-03-31"}),
])
def test_interpretar_comando(texto, esperado):
    assert comandos.interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["avancar 5", "/avancar 0", "/avancar 999", "/avancar amanhã", ""])
def test_comando_invalido(texto):
    with pytest.raises(ValueError):
        comandos.interpretar(texto)


def test_cenario_automatico_anda_sozinho_ate_o_presente(raiz, monkeypatch):
    monkeypatch.setattr(cli, "_hoje", lambda: HOJE)
    meta = armazem.ler_json(raiz / "cenarios" / "teste" / "cenario.json")
    armazem.gravar_json(raiz / "cenarios" / "teste" / "cenario.json", meta | {"automatico": {"dias_por_execucao": 2}})
    assert cli.pendentes(HOJE) == ["teste"]  # ainda sem estado: a primeira execução funda a empresa
    config.usar_cenario("teste")
    _avancar(ate=date(2026, 9, 29))
    assert cli.pendentes(HOJE) == ["teste"]
    assert cli.main(["--cenario", "teste", "avancar", "--automatico", "--sem-extracao"]) == 0
    estado = armazem.ler_json(config.DADOS / "estado.json")
    assert estado["ultima_data"] == "2026-10-01"  # dois dias por execução, sem passar de ontem
    assert cli.pendentes(HOJE) == []


def test_avanco_baixa_adiantado_e_depois_simula_sem_extrair(raiz):
    config.usar_cenario("teste")
    chamadas = []
    conectores = {f: (lambda c: lambda i, f_: (chamadas.append(f_), c(i, f_))[1])(c)
                  for f, c in fake_conectores().items()}
    cli.avancar(dias=1, conectores=conectores, hoje=HOJE)
    assert max(chamadas).isoformat() == "2026-08-18"  # 04/08 + 10 dias úteis baixados adiantado
    chamadas.clear()
    assert cli.avancar(dias=5, conectores=conectores, hoje=HOJE) == ["2026-08-05", "2026-08-06", "2026-08-07",
                                                                     "2026-08-10", "2026-08-11"]
    assert chamadas == []  # o passado já estava baixado: só simulou
    reg = armazem.ler_json(config.DIAS / "2026-08-11.json")
    assert reg["incidentes_do_dia"] == [] or all(i["tipo"] != "falha_real" for i in reg["incidentes_do_dia"])
    cli.avancar(dias=10, conectores=conectores, hoje=HOJE)
    assert chamadas  # passou do que estava baixado: extrai de novo
