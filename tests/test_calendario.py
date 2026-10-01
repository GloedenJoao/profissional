from datetime import date

from gestora import calendario as c


def test_pascoa():
    assert c.pascoa(2026) == date(2026, 4, 5)
    assert c.pascoa(2027) == date(2027, 3, 28)


def test_feriados_b3():
    assert not c.dia_util(date(2026, 2, 16))  # carnaval
    assert not c.dia_util(date(2026, 4, 3))   # sexta-feira santa
    assert not c.dia_util(date(2026, 11, 20))
    assert not c.dia_util(date(2026, 10, 3))  # sábado
    assert c.dia_util(date(2026, 10, 1))


def test_navegacao():
    assert c.dia_util_anterior(date(2026, 10, 5)) == date(2026, 10, 2)
    assert c.proximo_dia_util(date(2026, 10, 9)) == date(2026, 10, 13)  # 12/10 feriado
    assert c.dias_uteis_entre(date(2026, 10, 1), date(2026, 10, 6)) == [date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6)]
    assert c.defasagem(date(2026, 10, 1), date(2026, 10, 5)) == 2
    assert c.defasagem(date(2026, 10, 5), date(2026, 10, 5)) == 0
