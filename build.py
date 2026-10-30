"""Genera Market Screen: descarga datos, calcula, dibuja las figuras y escribe la web.

Uso:
    python build.py                 # descarga datos reales y genera _site/
    python build.py --salida docs   # otra carpeta de salida
    python build.py --cache datos_crudos.json   # reutiliza una descarga anterior (desarrollo)
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from marketscreen import calculos as C
from marketscreen import formato as F
from marketscreen import fuentes as S
from marketscreen import graficos as G

RAIZ = Path(__file__).resolve().parent
MADRID = ZoneInfo("Europe/Madrid")
MINIMO_VALORES = 450   # por debajo de esto no se publica: se conserva la versión anterior
LOGOS_TOP = 150        # logos de los N valores con más capitalización (sólo las casillas grandes los muestran)

log = logging.getLogger("marketscreen")


def descargar() -> list[S.Valor]:
    s = S.sesion()
    valores = S.componentes(s)
    S.cotizaciones(s, valores)
    S.historicos(s, valores)
    return valores


def construir(valores: list[S.Valor], salida: Path) -> dict:
    valores = C.deduplicar_clases(valores)
    omitidos = [v.ticker for v in valores if not (v.precio and v.cap and v.cierre_anterior)]
    validos = [v for v in valores if v.ticker not in set(omitidos)]
    if omitidos:
        log.warning("Omitidos por falta de datos (%d): %s", len(omitidos), ", ".join(omitidos))
    if len(validos) < MINIMO_VALORES:
        raise SystemExit(f"Sólo {len(validos)} valores con datos (mínimo {MINIMO_VALORES}); no se publica.")

    rents = {v.ticker: C.rentabilidades(v) for v in validos}
    total_cap = sum(v.cap for v in validos)
    periodos = [p[0] for p in C.PERIODOS]
    largo = {p[0]: p[2] for p in C.PERIODOS}

    # ── Sectores (orden fijo: de mayor a menor capitalización) ──
    por_sector: dict[str, list[S.Valor]] = {}
    for v in validos:
        por_sector.setdefault(v.sector, []).append(v)
    sectores = sorted(por_sector, key=lambda s: -sum(v.cap for v in por_sector[s]))
    nombre_es = {s: C.SECTORES_ES.get(s, s) for s in sectores}

    # ── Agregados por periodo ──
    resumen, sect_rent = {}, {}
    for p in periodos:
        con = [v for v in validos if p in rents[v.ticker]]
        indice = C.agregado([v.cap for v in con], [rents[v.ticker][p] for v in con]) if con else None
        filas = []
        for s in sectores:
            vs = [v for v in por_sector[s] if p in rents[v.ticker]]
            if not vs:
                continue
            r = C.agregado([v.cap for v in vs], [rents[v.ticker][p] for v in vs])
            filas.append({"sector": s, "nombre": nombre_es[s], "r": r,
                          "suben": sum(1 for v in vs if rents[v.ticker][p] > 0), "total": len(vs)})
        sect_rent[p] = {f["sector"]: f["r"] for f in filas}
        orden = sorted(filas, key=lambda f: f["r"])
        suben = sum(1 for v in con if rents[v.ticker][p] > 0)
        bajan = sum(1 for v in con if rents[v.ticker][p] < 0)
        resumen[p] = {
            "indice": F.pct(indice), "indice_signo": (indice or 0) >= 0,
            "suben": suben, "bajan": bajan, "total": len(con),
            "mejor": [orden[-1]["nombre"], F.pct(orden[-1]["r"])] if orden else None,
            "peor": [orden[0]["nombre"], F.pct(orden[0]["r"])] if orden else None,
            "_filas": orden, "_indice": indice,
        }

    # ── Nodos del mapa: raíz, sectores y valores ──
    ids, labels, parents, vcap, vigual, custom, tt, ht, tam = [], [], [], [], [], [], [], [], []
    ids.append("S&P 500"); labels.append("S&P 500"); parents.append("")
    vcap.append(total_cap); vigual.append(len(validos))
    custom.append(["S&P 500", f"{len(validos)} valores", "", F.cap(total_cap), ""])
    tt.append("%{label}")
    ht.append("<b>S&P 500</b><br>%{customdata[1]} · %{customdata[3]}<br>Variación: %{text}<extra></extra>")
    tam.append(14)
    for s in sectores:
        vs = por_sector[s]
        cs = sum(v.cap for v in vs)
        ids.append(f"sec:{s}"); labels.append(nombre_es[s]); parents.append("S&P 500")
        vcap.append(cs); vigual.append(len(vs))
        custom.append([nombre_es[s], f"{len(vs)} valores", "", F.cap(cs), F.pct(cs / total_cap, 1, signo=False)])
        tt.append("%{label}")
        ht.append("<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[3]} · %{customdata[4]} del índice"
                  "<br>Variación: %{text}<extra></extra>")
        tam.append(14)
        for v in sorted(vs, key=lambda v: -v.cap):
            ids.append(v.ticker); labels.append(v.ticker); parents.append(f"sec:{s}")
            vcap.append(v.cap); vigual.append(1)
            custom.append([v.nombre, nombre_es[s], F.num(v.precio) + " $", F.cap(v.cap), v.subindustria])
            tt.append("<b>%{label}</b><br>%{text}")
            ht.append("<b>%{customdata[0]}</b> · %{label}<br>%{customdata[4]}<br>Precio: %{customdata[2]}"
                      "<br>Capitalización: %{customdata[3]}<br>Variación: %{text}<extra></extra>")
            tam.append(G.tam_letra(v.cap / total_cap))
    nodos = dict(ids=ids, labels=labels, parents=parents, valores_cap=vcap, customdata=custom,
                 texttemplate=tt, hovertemplate=ht, tam_letra=tam)

    mapa_pp = {}
    for p in periodos:
        lim = G.rango_color([r[p] * 100 for r in rents.values() if p in r])
        colores, textos = [], []
        for i, nid in enumerate(ids):
            if nid == "S&P 500":
                r = resumen[p]["_indice"]
            elif nid.startswith("sec:"):
                r = sect_rent[p].get(nid[4:])
            else:
                r = rents[nid].get(p)
            # Las cabeceras (índice y sectores) van en gris neutro: el color es sólo para los valores.
            neutro = nid == "S&P 500" or nid.startswith("sec:")
            colores.append(0 if neutro or r is None else round(r * 100, 3))
            textos.append(F.pct(r))
        etiquetas = [(f"{labels[i]} · {textos[i]}" if (nid == "S&P 500" or nid.startswith("sec:")) else labels[i])
                     for i, nid in enumerate(ids)]
        mapa_pp[p] = {"colores": colores, "text": textos, "labels": etiquetas, "limite": lim,
                      "leyenda": [F.pct(-lim / 100, 1 if lim < 2 else 0), "0 %", F.pct(lim / 100, 1 if lim < 2 else 0)]}

    fig_mapa = G.mapa_base(nodos, "1D", mapa_pp)

    barras = {e: {p: json.loads(G.barras_sectores(resumen[p]["_filas"], resumen[p]["_indice"], largo[p], e).to_json())
                  for p in periodos} for e in G.ESCALAS}
    distrib = {e: {p: json.loads(G.distribucion([r[p] for r in rents.values() if p in r], largo[p], e).to_json())
                   for p in periodos} for e in G.ESCALAS}

    # ── Valores (para las listas, el buscador y la ficha) ──
    tabla = []
    for v in validos:
        r = rents[v.ticker]
        tabla.append({
            "t": v.ticker, "n": v.nombre, "s": sectores.index(v.sector), "sub": v.subindustria,
            "p": F.num(v.precio) + " $", "c": F.cap(v.cap), "cap": v.cap,
            "r": {k: round(x * 100, 3) for k, x in r.items()},
            "rt": {k: F.pct(x) for k, x in r.items()},
            "sp": C.minigrafico(v),
        })

    ahora = datetime.now(timezone.utc)
    hora_datos = max(v.hora for v in validos if v.hora)
    hd = datetime.fromtimestamp(hora_datos, MADRID)
    estados = {}
    for v in validos:
        estados[v.estado_mercado] = estados.get(v.estado_mercado, 0) + 1
    estado = max(estados, key=estados.get)
    abierto = estado == "REGULAR"
    sello = (f"Mercado abierto · precios con hasta 15 min de retraso · {F.fecha(hd)}, {hd:%H:%M} (hora de Madrid)"
             if abierto else f"Mercado cerrado · último precio {F.fecha(hd)}, {hd:%H:%M} (hora de Madrid)")

    # ── Logos de los valores más grandes (decoración: si fallan, el mapa sale sin ellos) ──
    grandes = sorted(validos, key=lambda v: -v.cap)[:LOGOS_TOP]
    imgs = S.logos([v.yahoo for v in grandes])
    logos = {v.ticker: f"logos/{v.yahoo}.webp" for v in grandes if v.yahoo in imgs}

    datos = {
        "generado": ahora.isoformat(timespec="seconds"),
        "hora_datos": hora_datos, "sello": sello, "abierto": abierto,
        "n": len(validos), "omitidos": omitidos,
        "periodos": [{"id": a, "corto": b, "largo": c} for a, b, c in C.PERIODOS],
        "sectores": [nombre_es[s] for s in sectores],
        "escalas": {k: {"nombre": e["nombre"], "colores": e["colores"]} for k, e in G.ESCALAS.items()},
        "resumen": {p: {k: x for k, x in d.items() if not k.startswith("_")} for p, d in resumen.items()},
        "mapa": {"figura": json.loads(fig_mapa.to_json()), "por_periodo": mapa_pp, "valores_igual": vigual},
        "barras": barras, "distribucion": distrib, "valores": tabla, "logos": logos,
    }

    salida.mkdir(parents=True, exist_ok=True)
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if imgs:
        (salida / "logos").mkdir(exist_ok=True)
        for sy, contenido in imgs.items():
            (salida / "logos" / f"{sy}.webp").write_bytes(contenido)
    for f in (RAIZ / "estatico").iterdir():
        shutil.copy(f, salida / f.name)
    import plotly
    env = Environment(loader=FileSystemLoader(RAIZ / "plantillas"), autoescape=select_autoescape(["html"]))
    html = env.get_template("index.html").render(
        r=resumen["1D"], sello=sello, n=len(validos), periodos=C.PERIODOS,
        sectores=[nombre_es[s] for s in sectores], escalas=G.ESCALAS,
        plotly_js=f"https://cdn.plot.ly/plotly-{plotly.offline.get_plotlyjs_version()}.min.js",
        version=int(ahora.timestamp()),
    )
    (salida / "index.html").write_text(html, encoding="utf-8")
    (salida / ".nojekyll").write_text("")
    log.info("Listo: %d valores, %d omitidos → %s", len(validos), len(omitidos), salida)
    return datos


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default="_site")
    ap.add_argument("--cache", help="JSON con una descarga previa; si no existe, se crea")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
    if a.cache and Path(a.cache).exists():
        valores = [S.Valor(**d) for d in json.loads(Path(a.cache).read_text())]
        log.info("Usando la descarga guardada en %s", a.cache)
    else:
        valores = descargar()
        if a.cache:
            Path(a.cache).write_text(json.dumps([asdict(v) for v in valores]))
    construir(valores, RAIZ / a.salida if not Path(a.salida).is_absolute() else Path(a.salida))


if __name__ == "__main__":
    main()
