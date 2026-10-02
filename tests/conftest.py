import io
import math
import shutil
import zipfile
from datetime import date, timedelta

import pytest

from gestora import calendario, config


def _dias(inicio, fim):
    return calendario.dias_uteis_entre(inicio - timedelta(days=1), fim)


def fake_conectores(falhar=()):
    """Conectores sintéticos e determinísticos com a mesma forma dos reais."""

    def checar(nome):
        if nome in falhar:
            raise RuntimeError(f"{nome} fora do ar (teste)")

    def sgs(inicio, fim):
        checar("bcb_sgs")
        dias = _dias(inicio, fim)
        ipca = []
        m = date(inicio.year - 2, inicio.month, 1)
        while m <= date(fim.year, fim.month, 1) - timedelta(days=40):
            ipca.append({"data": m.isoformat(), "valor": 0.35})
            m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        return {"cdi": [{"data": d.isoformat(), "valor": 0.050788} for d in dias],
                "selic": [{"data": d.isoformat(), "valor": 13.75} for d in dias],
                "dolar": [{"data": d.isoformat(), "valor": round(5.2 + 0.05 * math.sin(d.toordinal() / 3), 4)} for d in dias],
                "ipca": ipca}

    def ptax(inicio, fim):
        checar("bcb_ptax")
        return {"dolar_ptax": [{"data": d.isoformat(), "valor": round(5.2 + 0.05 * math.sin(d.toordinal() / 3), 4)}
                               for d in _dias(inicio, fim)]}

    def focus(inicio, fim):
        checar("bcb_focus")
        dias = _dias(inicio, fim)
        return {"focus_ipca": [{"data": d.isoformat(), "valor": 4.99} for d in dias],
                "focus_selic": [{"data": d.isoformat(), "valor": 13.5} for d in dias]}

    def tesouro(inicio, fim):
        checar("tesouro")
        linhas = []
        for d in _dias(inicio, fim):
            k = d.toordinal() - 739000
            linhas.append({"data": d.isoformat(), "tipo": "Tesouro Prefixado", "vencimento": "2029-01-01",
                           "taxa": 13.2, "pu": round(700 + 0.25 * k, 2)})
            linhas.append({"data": d.isoformat(), "tipo": "Tesouro IPCA+", "vencimento": "2035-05-15",
                           "taxa": 7.4, "pu": round(2000 + 0.6 * k, 2)})
        return {"tesouro": linhas}

    def yahoo(inicio, fim):
        checar("yahoo")
        dias = _dias(inicio, fim)
        return {"ibov": [{"data": d.isoformat(), "valor": round(185000 * (1 + 0.01 * math.sin(d.toordinal() / 5)), 2)} for d in dias],
                "bova11": [{"data": d.isoformat(), "valor": round(184 * (1 + 0.01 * math.sin(d.toordinal() / 5)), 2)} for d in dias]}

    def b3(inicio, fim):
        checar("b3")
        return {"bova11_b3": [{"data": d.isoformat(), "valor": round(184 * (1 + 0.01 * math.sin(d.toordinal() / 5)), 2)}
                              for d in _dias(inicio, fim)]}

    return {"bcb_sgs": sgs, "bcb_ptax": ptax, "bcb_focus": focus, "tesouro": tesouro, "yahoo": yahoo, "b3": b3}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Repositório isolado: dados/ e empresa/ em pasta temporária, com as políticas reais."""
    dados, empresa = tmp_path / "dados", tmp_path / "empresa"
    (empresa / "decisoes").mkdir(parents=True)
    shutil.copy(config.POLITICAS, empresa / "politicas.json")
    monkeypatch.setattr(config, "DADOS", dados)
    monkeypatch.setattr(config, "SERIES", dados / "series")
    monkeypatch.setattr(config, "DIAS", dados / "dias")
    monkeypatch.setattr(config, "EMPRESA", empresa)
    monkeypatch.setattr(config, "DECISOES", empresa / "decisoes")
    monkeypatch.setattr(config, "POLITICAS", empresa / "politicas.json")
    return tmp_path


def zip_cotahist(linhas):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("COTAHIST_D30092026.TXT", "\n".join(linhas))
    return buf.getvalue()
