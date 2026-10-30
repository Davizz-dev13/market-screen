"""Formato de números a la española: coma decimal, punto de millares."""
from __future__ import annotations

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def num(x: float, dec: int = 2) -> str:
    s = f"{x:,.{dec}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(r: float | None, dec: int = 2, signo: bool = True) -> str:
    if r is None:
        return "—"
    v = r * 100
    txt = num(abs(v), dec)
    if signo:
        txt = ("+" if v > 0 else "−" if v < 0 else "") + txt
    return f"{txt} %"


def cap(x: float | None) -> str:
    if not x:
        return "—"
    if x >= 1e12:
        return f"{num(x / 1e12, 2)} bill. $"
    if x >= 1e9:
        return f"{num(x / 1e9, 1)} mil M$"
    return f"{num(x / 1e6, 0)} M$"


def fecha(d) -> str:
    return f"{d.day} {MESES[d.month - 1]} {d.year}"
