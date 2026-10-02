"""Conectores das fontes públicas. Cada um devolve {serie: [linhas]}.

Linhas de séries simples: {"data": "AAAA-MM-DD", "valor": float}.
Linhas do Tesouro: {"data", "tipo", "vencimento", "taxa", "pu"}.

O parse fica separado do download para ser testado com respostas gravadas.
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone

from . import calendario

AGENTE_HTTP = "Mozilla/5.0 (capivara-asset; simulacao ficticia; github.com/GloedenJoao/profissional)"


class FonteIndisponivel(Exception):
    pass


def baixar(url: str, tentativas: int = 3, timeout: int = 90) -> bytes:
    """GET com retry e backoff exponencial. 404 não é retentado."""
    erro: Exception | None = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE_HTTP, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            erro = e
            if e.code == 404:
                break
        except Exception as e:  # noqa: BLE001 - rede: qualquer falha vira nova tentativa
            erro = e
        if i < tentativas - 1:
            time.sleep(2 ** (i + 1))
    raise FonteIndisponivel(f"{url[:120]}: {erro}")


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _iso_de_br(s: str) -> str:
    return datetime.strptime(s.strip(), "%d/%m/%Y").date().isoformat()


def _num_br(s: str) -> float:
    return float(s.strip().replace(".", "").replace(",", "."))


# ---------------------------------------------------------------- BCB SGS
SGS = {"cdi": 12, "selic": 432, "dolar": 1, "ipca": 433}


def parse_sgs(payload: bytes, fim: date) -> list[dict]:
    dados = json.loads(payload)
    if not isinstance(dados, list):
        raise ValueError(f"SGS: resposta inesperada {str(dados)[:200]}")
    linhas = []
    for item in dados:
        iso = _iso_de_br(item["data"])
        if iso <= fim.isoformat():  # a Selic meta vem preenchida para datas futuras
            linhas.append({"data": iso, "valor": float(item["valor"])})
    return linhas


def extrair_bcb_sgs(inicio: date, fim: date, http=baixar) -> dict[str, list[dict]]:
    saida = {}
    for serie, codigo in SGS.items():
        ini = inicio - timedelta(days=430) if serie == "ipca" else inicio
        url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json"
               f"&dataInicial={_br(ini)}&dataFinal={_br(fim + timedelta(days=40))}")
        saida[serie] = parse_sgs(http(url), fim)
    return saida


# ---------------------------------------------------------------- BCB PTAX
def parse_ptax(payload: bytes, fim: date) -> list[dict]:
    valores = json.loads(payload)["value"]
    por_dia: dict[str, float] = {}
    for v in valores:
        iso = v["dataHoraCotacao"][:10]
        if iso <= fim.isoformat():
            por_dia[iso] = float(v["cotacaoVenda"])  # a última cotação do dia é a de fechamento
    return [{"data": d, "valor": por_dia[d]} for d in sorted(por_dia)]


def extrair_bcb_ptax(inicio: date, fim: date, http=baixar) -> dict[str, list[dict]]:
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
           "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
           f"?@dataInicial='{inicio:%m-%d-%Y}'&@dataFinalCotacao='{fim:%m-%d-%Y}'"
           "&$format=json&$select=cotacaoVenda,dataHoraCotacao")
    return {"dolar_ptax": parse_ptax(http(url), fim)}


# ---------------------------------------------------------------- BCB Focus
def parse_focus(payload: bytes, fim: date) -> dict[str, list[dict]]:
    valores = json.loads(payload)["value"]
    series: dict[str, dict[str, float]] = {"focus_ipca": {}, "focus_selic": {}}
    for v in valores:
        d = v["Data"][:10]
        if d > fim.isoformat() or str(v["DataReferencia"]) != d[:4]:
            continue
        nome = "focus_ipca" if v["Indicador"] == "IPCA" else "focus_selic"
        series[nome][d] = float(v["Mediana"])
    return {k: [{"data": d, "valor": s[d]} for d in sorted(s)] for k, s in series.items()}


def extrair_bcb_focus(inicio: date, fim: date, http=baixar) -> dict[str, list[dict]]:
    filtro = (f"(Indicador eq 'IPCA' or Indicador eq 'Selic') and baseCalculo eq 0 "
              f"and Data ge '{(inicio - timedelta(days=10)).isoformat()}'")
    q = urllib.parse.urlencode({"$filter": filtro, "$select": "Indicador,Data,DataReferencia,Mediana",
                                "$format": "json", "$top": "20000"}, quote_via=urllib.parse.quote)
    url = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?" + q
    return parse_focus(http(url), fim)


# ---------------------------------------------------------------- Tesouro Direto
TESOURO_URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
               "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
TIPOS_TESOURO = {"Tesouro Prefixado", "Tesouro IPCA+"}
COLUNAS_TESOURO = ["Tipo Titulo", "Data Vencimento", "Data Base", "Taxa Compra Manha", "PU Base Manha"]


def parse_tesouro(payload: bytes, inicio: date, fim: date) -> list[dict]:
    texto = payload.decode("latin-1" if payload[:3] != b"\xef\xbb\xbf" else "utf-8-sig")
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
    faltando = [c for c in COLUNAS_TESOURO if c not in (leitor.fieldnames or [])]
    if faltando:
        raise ValueError(f"Tesouro: colunas ausentes {faltando}; cabeçalho {leitor.fieldnames}")
    ini, f = inicio.isoformat(), fim.isoformat()
    linhas = []
    for r in leitor:
        if r["Tipo Titulo"] not in TIPOS_TESOURO:
            continue
        d = _iso_de_br(r["Data Base"])
        if ini <= d <= f:
            linhas.append({"data": d, "tipo": r["Tipo Titulo"], "vencimento": _iso_de_br(r["Data Vencimento"]),
                           "taxa": _num_br(r["Taxa Compra Manha"]), "pu": _num_br(r["PU Base Manha"])})
    return linhas


def extrair_tesouro(inicio: date, fim: date, http=baixar) -> dict[str, list[dict]]:
    return {"tesouro": parse_tesouro(http(TESOURO_URL, timeout=180), inicio, fim)}


# ---------------------------------------------------------------- Yahoo Finance
BRT = timezone(timedelta(hours=-3))


def parse_yahoo(payload: bytes, fim: date) -> list[dict]:
    res = json.loads(payload)["chart"]
    if res.get("error"):
        raise ValueError(f"Yahoo: {res['error']}")
    r = res["result"][0]
    fechamentos = r["indicators"]["quote"][0]["close"]
    linhas = {}
    for ts, v in zip(r.get("timestamp") or [], fechamentos):
        if v is None:
            continue
        d = datetime.fromtimestamp(ts, BRT).date()
        if d <= fim:
            linhas[d.isoformat()] = round(float(v), 4)
    return [{"data": d, "valor": linhas[d]} for d in sorted(linhas)]


def extrair_yahoo(inicio: date, fim: date, http=baixar) -> dict[str, list[dict]]:
    p1 = int(datetime.combine(inicio - timedelta(days=5), datetime.min.time(), BRT).timestamp())
    p2 = int(datetime.combine(fim + timedelta(days=1), datetime.max.time(), BRT).timestamp())
    saida = {}
    for serie, simbolo in {"ibov": "%5EBVSP", "bova11": "BOVA11.SA"}.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}?period1={p1}&period2={p2}&interval=1d"
        saida[serie] = parse_yahoo(http(url), fim)
    return saida


# ---------------------------------------------------------------- B3 COTAHIST
def parse_cotahist(payload: bytes, codigo: str = "BOVA11") -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        texto = z.read(z.namelist()[0]).decode("latin-1")
    linhas = []
    for ln in texto.splitlines():
        if ln[:2] == "01" and ln[12:24].strip() == codigo:
            d = datetime.strptime(ln[2:10], "%Y%m%d").date().isoformat()
            linhas.append({"data": d, "valor": int(ln[108:121]) / 100})
    return linhas


def extrair_b3(inicio: date, fim: date, http=baixar) -> dict[str, list[dict]]:
    dias = calendario.dias_uteis_entre(calendario.dia_util_anterior(inicio), fim)[-30:]
    linhas, erros = [], []
    for d in dias:
        try:
            linhas += parse_cotahist(http(f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{d:%d%m%Y}.ZIP"))
        except Exception as e:  # noqa: BLE001 - arquivo do dia ainda não publicado não é falha da fonte
            erros.append(f"{d}: {e}")
    if not linhas and dias:
        raise FonteIndisponivel("; ".join(erros[-3:]))
    return {"bova11_b3": linhas}


CONECTORES = {
    "bcb_sgs": extrair_bcb_sgs,
    "bcb_ptax": extrair_bcb_ptax,
    "bcb_focus": extrair_bcb_focus,
    "tesouro": extrair_tesouro,
    "yahoo": extrair_yahoo,
    "b3": extrair_b3,
}
