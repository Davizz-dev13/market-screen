"""Descarga de datos reales.

- Componentes del S&P 500 y su sector GICS: tabla "constituents" de Wikipedia.
- Cotización actual y capitalización: endpoint de cotizaciones de Yahoo Finance (v7/quote).
- Histórico diario de cierres (2 años): endpoint "spark" de Yahoo Finance (v8/spark).

Yahoo limita las peticiones sin navegador (error 429), así que usamos curl_cffi
haciéndonos pasar por Chrome. Si un valor falla, se omite y se apunta en el log:
nunca se inventa ni se rellena un dato.
"""
from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field

import pandas as pd
from curl_cffi import requests as cr

log = logging.getLogger("marketscreen")

LOGO_URL = "https://companiesmarketcap.com/img/company-logos/128/{}.webp"   # el mismo origen que Big Tech
LOGO_ALIAS = {"GOOGL": "GOOG", "FOXA": "FOX", "NWSA": "NWS"}
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
YH = "https://query1.finance.yahoo.com"


@dataclass
class Valor:
    ticker: str          # como lo escribe Wikipedia (BRK.B)
    yahoo: str           # como lo pide Yahoo (BRK-B)
    nombre: str
    sector: str          # sector GICS en inglés
    subindustria: str
    cik: str = ""
    precio: float | None = None
    cierre_anterior: float | None = None
    cap: float | None = None
    moneda: str | None = None
    hora: int | None = None          # epoch del último precio
    estado_mercado: str | None = None
    fechas: list[int] = field(default_factory=list)   # epoch de cada cierre diario
    cierres: list[float] = field(default_factory=list)


def sesion() -> cr.Session:
    return cr.Session(impersonate="chrome")


def _get(s: cr.Session, url: str, params: dict | None = None, intentos: int = 4, pausa: float = 2.0):
    ultimo = None
    for i in range(intentos):
        try:
            r = s.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r
            ultimo = f"HTTP {r.status_code}"
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(pausa * (2 ** i))
                continue
            break
        except Exception as e:  # red caída, timeout...
            ultimo = repr(e)
            time.sleep(pausa * (2 ** i))
    raise RuntimeError(f"{url}: {ultimo}")


def componentes(s: cr.Session) -> list[Valor]:
    r = _get(s, WIKI_URL)
    tabla = pd.read_html(io.StringIO(r.text), attrs={"id": "constituents"})[0]
    valores = []
    for _, f in tabla.iterrows():
        t = str(f["Symbol"]).strip()
        valores.append(Valor(
            ticker=t,
            yahoo=t.replace(".", "-"),
            nombre=str(f["Security"]).strip(),
            sector=str(f["GICS Sector"]).strip(),
            subindustria=str(f["GICS Sub-Industry"]).strip(),
            cik=str(f.get("CIK", "")).strip(),
        ))
    log.info("Wikipedia: %d componentes", len(valores))
    return valores


def _crumb(s: cr.Session) -> str:
    try:
        s.get("https://fc.yahoo.com", timeout=20)
    except Exception:
        pass  # sólo sirve para recibir la cookie; da igual si responde 404
    r = _get(s, f"{YH}/v1/test/getcrumb")
    crumb = r.text.strip()
    if not crumb or "<" in crumb:
        raise RuntimeError("Yahoo no ha devuelto crumb")
    return crumb


def cotizaciones(s: cr.Session, valores: list[Valor], lote: int = 100) -> None:
    crumb = _crumb(s)
    por_simbolo = {v.yahoo: v for v in valores}
    campos = ("regularMarketPrice,regularMarketPreviousClose,marketCap,currency,"
              "regularMarketTime,marketState,shortName")
    simbolos = list(por_simbolo)
    for i in range(0, len(simbolos), lote):
        trozo = simbolos[i:i + lote]
        r = _get(s, f"{YH}/v7/finance/quote",
                 {"symbols": ",".join(trozo), "crumb": crumb, "fields": campos})
        for q in r.json().get("quoteResponse", {}).get("result", []):
            v = por_simbolo.get(q.get("symbol"))
            if not v:
                continue
            v.precio = q.get("regularMarketPrice")
            v.cierre_anterior = q.get("regularMarketPreviousClose")
            v.cap = q.get("marketCap")
            v.moneda = q.get("currency")
            v.hora = q.get("regularMarketTime")
            v.estado_mercado = q.get("marketState")
        time.sleep(0.3)
    sin = [v.ticker for v in valores if not v.precio or not v.cap]
    if sin:
        log.warning("Sin cotización o capitalización (%d): %s", len(sin), ", ".join(sin))


def historicos(s: cr.Session, valores: list[Valor], lote: int = 20, rango: str = "2y") -> None:
    por_simbolo = {v.yahoo: v for v in valores}
    simbolos = list(por_simbolo)
    for i in range(0, len(simbolos), lote):
        trozo = simbolos[i:i + lote]
        try:
            r = _get(s, f"{YH}/v8/finance/spark",
                     {"symbols": ",".join(trozo), "range": rango, "interval": "1d"})
            datos = r.json()
        except Exception as e:
            log.warning("Histórico fallido para %s: %s", ",".join(trozo), e)
            continue
        for sym, d in datos.items():
            v = por_simbolo.get(sym)
            if not v or not isinstance(d, dict):
                continue
            ts, cl = d.get("timestamp") or [], d.get("close") or []
            pares = [(t, c) for t, c in zip(ts, cl) if c is not None]
            v.fechas = [t for t, _ in pares]
            v.cierres = [float(c) for _, c in pares]
        time.sleep(0.25)
    sin = [v.ticker for v in valores if len(v.cierres) < 30]
    if sin:
        log.warning("Sin histórico suficiente (%d): %s", len(sin), ", ".join(sin))


def logos(simbolos: list[str], hilos: int = 8) -> dict[str, bytes]:
    """Logos (WebP de 128 px) de los valores con más peso, por su símbolo de Yahoo (BRK-B).

    Son sólo decoración: el que falla se queda sin logo y la web se genera igual.
    """
    from concurrent.futures import ThreadPoolExecutor

    def uno(sy: str):
        s = sesion()
        for cand in dict.fromkeys([sy, LOGO_ALIAS.get(sy, sy)]):
            try:
                r = s.get(LOGO_URL.format(cand), timeout=15)
                if r.status_code == 200 and r.content[:4] == b"RIFF":
                    return sy, r.content
            except Exception as e:
                log.info("%s: sin logo (%r)", sy, e)
        return sy, None

    try:
        with ThreadPoolExecutor(hilos) as ex:
            res = dict(x for x in ex.map(uno, simbolos) if x[1])
    except Exception as e:  # nunca tumba la publicación por un logo
        log.warning("Logos: %r", e)
        return {}
    log.info("Logos: %d de %d", len(res), len(simbolos))
    return res
