"""Rentabilidades por periodo, agregados por sector y minigráficos."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .fuentes import Valor

log = logging.getLogger("marketscreen")
NY = ZoneInfo("America/New_York")

# id, etiqueta corta (botón), descripción larga
PERIODOS = [
    ("1D", "1D", "en la sesión"),
    ("1S", "1S", "en una semana"),
    ("1M", "1M", "en un mes"),
    ("3M", "3M", "en tres meses"),
    ("YTD", "YTD", "en lo que va de año"),
    ("1A", "1A", "en un año"),
]

SECTORES_ES = {
    "Information Technology": "Tecnología",
    "Financials": "Finanzas",
    "Health Care": "Salud",
    "Consumer Discretionary": "Consumo discrecional",
    "Communication Services": "Comunicaciones",
    "Industrials": "Industria",
    "Consumer Staples": "Consumo básico",
    "Energy": "Energía",
    "Utilities": "Servicios públicos",
    "Real Estate": "Inmobiliario",
    "Materials": "Materiales",
}


def dia_ny(epoch: int) -> date:
    return datetime.fromtimestamp(epoch, NY).date()


def _menos_meses(d: date, meses: int) -> date:
    m = d.month - 1 - meses
    a = d.year + m // 12
    m = m % 12 + 1
    dia = min(d.day, [31, 29 if a % 4 == 0 and (a % 100 or a % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(a, m, dia)


def fecha_referencia(periodo: str, hoy: date) -> date | None:
    """Último día cuyo cierre sirve de base para el periodo (cierre en o antes de esa fecha)."""
    if periodo == "1S":
        return hoy - timedelta(days=7)
    if periodo == "1M":
        return _menos_meses(hoy, 1)
    if periodo == "3M":
        return _menos_meses(hoy, 3)
    if periodo == "YTD":
        return date(hoy.year - 1, 12, 31)
    if periodo == "1A":
        return _menos_meses(hoy, 12)
    return None


def cierre_en(v: Valor, d: date) -> float | None:
    base = None
    for t, c in zip(v.fechas, v.cierres):
        if dia_ny(t) <= d:
            base = c
        else:
            break
    return base


def deduplicar_clases(valores: list[Valor]) -> list[Valor]:
    """GOOGL/GOOG, FOXA/FOX, NWSA/NWS: Yahoo da la capitalización de toda la empresa
    en cada clase, así que contarlas dos veces duplicaría su peso. Nos quedamos con
    una clase por empresa (la clase A cuando existe) y apuntamos la otra."""
    por_cik: dict[str, list[Valor]] = {}
    for v in valores:
        por_cik.setdefault(v.cik or v.ticker, []).append(v)
    fuera = set()
    for grupo in por_cik.values():
        if len(grupo) < 2:
            continue
        grupo.sort(key=lambda v: (0 if "Class A" in v.nombre else 1, len(v.ticker)))
        for v in grupo[1:]:
            fuera.add(v.ticker)
            log.info("Clase duplicada omitida: %s (se usa %s)", v.ticker, grupo[0].ticker)
    return [v for v in valores if v.ticker not in fuera]


def rentabilidades(v: Valor) -> dict[str, float]:
    """Rentabilidad en tanto por uno para cada periodo con datos; los que faltan no aparecen."""
    out: dict[str, float] = {}
    if v.precio and v.cierre_anterior:
        out["1D"] = v.precio / v.cierre_anterior - 1
    if not v.precio or not v.fechas or not v.hora:
        return out
    hoy = dia_ny(v.hora)
    for pid, _, _ in PERIODOS[1:]:
        ref = fecha_referencia(pid, hoy)
        base = cierre_en(v, ref)
        # Sin histórico que llegue a la fecha de referencia (salida a bolsa reciente): se omite.
        if base and dia_ny(v.fechas[0]) <= ref:
            out[pid] = v.precio / base - 1
    return out


def agregado(caps: list[float], rents: list[float]) -> float | None:
    """Rentabilidad de una cartera ponderada por capitalización: cap actual / cap inicial - 1."""
    ahora = sum(caps)
    inicio = sum(c / (1 + r) for c, r in zip(caps, rents))
    return ahora / inicio - 1 if inicio else None


def minigrafico(v: Valor, ancho: int = 100, alto: int = 32, puntos: int = 125) -> str:
    """Trayecto SVG del último año (cierres diarios submuestreados), con el precio actual al final."""
    if not v.fechas or not v.hora:
        return ""
    desde = fecha_referencia("1A", dia_ny(v.hora))
    serie = [c for t, c in zip(v.fechas, v.cierres) if dia_ny(t) >= desde]
    if v.precio:
        if serie and v.fechas and dia_ny(v.fechas[-1]) == dia_ny(v.hora):
            serie[-1] = v.precio
        else:
            serie.append(v.precio)
    if len(serie) < 5:
        return ""
    paso = max(1, len(serie) // puntos)
    muestra = serie[::paso]
    if muestra[-1] != serie[-1]:
        muestra.append(serie[-1])
    lo, hi = min(muestra), max(muestra)
    rango = hi - lo or 1
    n = len(muestra) - 1
    pts = []
    for i, c in enumerate(muestra):
        x = i * ancho / n
        y = alto - (c - lo) / rango * alto
        pts.append(f"{x:.1f} {y:.1f}")
    return "M" + "L".join(pts)
