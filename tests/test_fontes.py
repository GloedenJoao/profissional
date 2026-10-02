"""Parsers com amostras das respostas reais (capturadas pela sonda no GitHub Actions)."""
import json
from datetime import date

import pytest

from gestora import fontes

from .conftest import zip_cotahist

FIM = date(2026, 10, 1)


def test_sgs_corta_datas_futuras():
    payload = b'[{"data":"30/09/2026","valor":"13.75"},{"data":"02/11/2026","valor":"13.75"}]'
    assert fontes.parse_sgs(payload, FIM) == [{"data": "2026-09-30", "valor": 13.75}]


def test_sgs_resposta_html_quebra():
    with pytest.raises(Exception):
        fontes.parse_sgs(b"<html>Requisicao invalida</html>", FIM)


def test_ptax_pega_ultima_cotacao_do_dia():
    payload = json.dumps({"value": [
        {"cotacaoVenda": 5.1111, "dataHoraCotacao": "2026-09-21 10:08:10.246"},
        {"cotacaoVenda": 5.1180, "dataHoraCotacao": "2026-09-21 13:09:00.000"},
        {"cotacaoVenda": 5.2000, "dataHoraCotacao": "2026-09-22 13:05:00.000"}]}).encode()
    assert fontes.parse_ptax(payload, FIM) == [{"data": "2026-09-21", "valor": 5.118}, {"data": "2026-09-22", "valor": 5.2}]


def test_focus_so_ano_corrente():
    payload = json.dumps({"value": [
        {"Indicador": "IPCA", "Data": "2026-09-25", "DataReferencia": "2026", "Mediana": 4.9915},
        {"Indicador": "IPCA", "Data": "2026-09-25", "DataReferencia": "2027", "Mediana": 4.3118},
        {"Indicador": "Selic", "Data": "2026-09-25", "DataReferencia": "2026", "Mediana": 13.5}]}).encode()
    s = fontes.parse_focus(payload, FIM)
    assert s["focus_ipca"] == [{"data": "2026-09-25", "valor": 4.9915}]
    assert s["focus_selic"] == [{"data": "2026-09-25", "valor": 13.5}]


def test_tesouro_csv_real():
    csv = ("Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha\n"
           "Tesouro Selic;01/03/2028;30/09/2026;0,03;0,04;19988,07;19975,02;19975,02\n"
           "Tesouro Prefixado;01/01/2029;30/09/2026;13,21;13,33;754,10;753,20;753,20\n"
           "Tesouro IPCA+;15/05/2035;30/09/2026;7,40;7,52;2.101,55;2.098,10;2.098,10\n"
           "Tesouro Prefixado;01/01/2026;31/10/2025;14,83;14,95;977,75;977,04;977,04\n").encode("latin-1")
    linhas = fontes.parse_tesouro(csv, date(2026, 9, 1), FIM)
    assert linhas == [
        {"data": "2026-09-30", "tipo": "Tesouro Prefixado", "vencimento": "2029-01-01", "taxa": 13.21, "pu": 753.2},
        {"data": "2026-09-30", "tipo": "Tesouro IPCA+", "vencimento": "2035-05-15", "taxa": 7.4, "pu": 2098.1}]


def test_tesouro_mudou_formato():
    with pytest.raises(ValueError, match="colunas ausentes"):
        fontes.parse_tesouro(b"Titulo;Vencimento;Data\nx;y;z\n", date(2026, 9, 1), FIM)


def test_yahoo():
    payload = json.dumps({"chart": {"error": None, "result": [{
        "timestamp": [1790773200, 1790859600], "indicators": {"quote": [{"close": [186340.4, None]}]}}]}}).encode()
    assert fontes.parse_yahoo(payload, FIM) == [{"data": "2026-09-30", "valor": 186340.4}]


def test_cotahist_bova11():
    linha = "01" + "20260930" + "02" + "BOVA11".ljust(12) + " " * 84 + "0000000018441" + " " * 50
    outra = "01" + "20260930" + "02" + "PETR4".ljust(12) + " " * 84 + "0000000003800" + " " * 50
    assert fontes.parse_cotahist(zip_cotahist(["00HEADER", linha, outra])) == [{"data": "2026-09-30", "valor": 184.41}]
