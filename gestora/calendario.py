"""Calendário de dias úteis da B3 (feriados nacionais + datas sem pregão)."""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


@lru_cache(maxsize=None)
def feriados(ano: int) -> frozenset[date]:
    p = pascoa(ano)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 24), (12, 25), (12, 31)]
    dias = {date(ano, m, d) for m, d in fixos}
    if ano >= 2024:
        dias.add(date(ano, 11, 20))  # Consciência Negra, feriado nacional desde 2024
    dias |= {p - timedelta(days=48), p - timedelta(days=47), p - timedelta(days=2), p + timedelta(days=60)}
    return frozenset(dias)


def dia_util(d: date) -> bool:
    return d.weekday() < 5 and d not in feriados(d.year)


def proximo_dia_util(d: date) -> date:
    d += timedelta(days=1)
    while not dia_util(d):
        d += timedelta(days=1)
    return d


def dia_util_anterior(d: date) -> date:
    d -= timedelta(days=1)
    while not dia_util(d):
        d -= timedelta(days=1)
    return d


def dias_uteis_entre(inicio: date, fim: date) -> list[date]:
    """Dias úteis em (inicio, fim], em ordem."""
    dias, d = [], inicio
    while True:
        d = proximo_dia_util(d)
        if d > fim:
            return dias
        dias.append(d)


def defasagem(ultima: date | None, esperada: date) -> int:
    """Quantos dias úteis a última data disponível está atrás da esperada (0 = em dia)."""
    if ultima is None:
        return 99
    if ultima >= esperada:
        return 0
    return len(dias_uteis_entre(ultima, esperada))


def corte_publicacao(regra: str, d: date) -> tuple[date, date]:
    """(até que data de referência uma série com esta regra pode ser vista às 08h de `d`, data esperada).

    A primeira serve para cortar a série (nada depois dela existe para a empresa); a segunda é o que uma fonte em
    dia já teria publicado. Regras em config.PUBLICACAO."""
    if regra == "d":
        return d, d
    if regra == "d-1":
        return d - timedelta(days=1), dia_util_anterior(d)
    if regra == "semanal":
        segunda = d - timedelta(days=d.weekday())
        return segunda - timedelta(days=1), dia_util_anterior(segunda)
    if regra == "mensal":
        recuo = 1 if d.day >= 15 else 2
        mes = d.month - recuo
        ref = date(d.year + (mes - 1) // 12, (mes - 1) % 12 + 1, 1)
        return ref, ref
    raise ValueError(f"regra de publicação desconhecida: {regra}")
