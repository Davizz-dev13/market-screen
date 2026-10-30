"""Pruebas de los cálculos y del formato (python -m pytest)."""
from datetime import date, datetime, timezone

from marketscreen import calculos as C
from marketscreen import formato as F
from marketscreen.fuentes import Valor


def ts(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 20, 0, tzinfo=timezone.utc).timestamp())


def test_formato_espanol():
    assert F.pct(0.012345) == "+1,23 %"
    assert F.pct(-0.5) == "−50,00 %"
    assert F.pct(None) == "—"
    assert F.num(1234567.891) == "1.234.567,89"
    assert F.cap(3.94e12) == "3,94 bill. $"
    assert F.cap(48.5e9) == "48,5 mil M$"


def test_fechas_de_referencia():
    hoy = date(2026, 3, 31)
    assert C.fecha_referencia("1S", hoy) == date(2026, 3, 24)
    assert C.fecha_referencia("1M", hoy) == date(2026, 2, 28)
    assert C.fecha_referencia("YTD", hoy) == date(2025, 12, 31)
    assert C.fecha_referencia("1A", hoy) == date(2025, 3, 31)


def test_agregado_ponderado():
    # Dos valores: uno duplica y otro se queda igual; ahora pesan 200 y 100.
    assert abs(C.agregado([200, 100], [1.0, 0.0]) - 0.5) < 1e-12


def test_rentabilidades_y_cierre_de_referencia():
    dias = [date(2025, 12, 30), date(2025, 12, 31), date(2026, 1, 2), date(2026, 1, 9)]
    v = Valor("X", "X", "X Corp", "Energy", "Oil", precio=110.0, cierre_anterior=100.0,
              cap=1e9, hora=ts(date(2026, 1, 9)), fechas=[ts(d) for d in dias], cierres=[90, 100, 105, 110])
    r = C.rentabilidades(v)
    assert abs(r["1D"] - 0.10) < 1e-12
    assert abs(r["YTD"] - 0.10) < 1e-12          # base: cierre del 31 de diciembre
    assert abs(r["1S"] - (110 / 105 - 1)) < 1e-12  # base: cierre del 2 de enero
    assert "1A" not in r                           # no hay histórico tan antiguo: se omite


def test_clases_duplicadas():
    a = Valor("GOOGL", "GOOGL", "Alphabet Inc. (Class A)", "Communication Services", "", cik="1652044")
    c = Valor("GOOG", "GOOG", "Alphabet Inc. (Class C)", "Communication Services", "", cik="1652044")
    m = Valor("MSFT", "MSFT", "Microsoft", "Information Technology", "", cik="789019")
    assert [v.ticker for v in C.deduplicar_clases([c, a, m])] == ["GOOGL", "MSFT"]
