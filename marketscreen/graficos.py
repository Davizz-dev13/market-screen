"""Figuras de Plotly diseñadas en Python.

El navegador sólo las dibuja: la página carga datos.json y le pasa estas
figuras tal cual a Plotly.js. Al cambiar de periodo, de grupo o de escala de
color, el JavaScript intercambia los arrays que aquí se precalculan.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go

from . import formato as F

FUENTE = "CMU, Georgia, 'Times New Roman', serif"
TINTA = "#1a1a1a"
GRIS = "#555555"
PAPEL = "#ffffff"
REJILLA = "#141414"
# El mapa va en una sans gruesa (la del sistema: San Francisco en iPhone/Mac, Segoe en Windows,
# Roboto en Android); las cabeceras de sector son una franja oscura del mismo tono que la rejilla.
FUENTE_MAPA = ("-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', 'Segoe UI', "
               "Roboto, Arial, sans-serif")
CABECERA = REJILLA
TEXTO_CABECERA = "#e9e9e6"

# Escalas divergentes con el centro en un gris cálido muy claro. En rojo y verde
# el color se satura pronto (una caída pequeña ya se ve roja) y oscurece hacia los
# extremos; Plotly pone el texto en blanco o negro según el fondo.
ESCALAS = {
    "rv": {  # rojo-verde, los mismos tonos que Sharpe Lab
        "nombre": "Rojo y verde",
        "colores": [[0.0, "#6e0000"], [0.2, "#9e0000"], [0.35, "#c40000"], [0.43, "#e00000"],
                    [0.475, "#ec6a64"], [0.5, "#ecebe6"], [0.525, "#6cc07f"], [0.57, "#12a039"],
                    [0.65, "#0b8a2e"], [0.8, "#086b23"], [1.0, "#044516"]],
    },
    "ab": {  # apto para daltónicos
        "nombre": "Naranja y azul",
        "colores": [[0.0, "#7a3a00"], [0.2, "#b35806"], [0.4, "#f2c690"], [0.5, "#ecebe6"],
                    [0.6, "#b3c8e4"], [0.8, "#1a3f8b"], [1.0, "#0f2659"]],
    },
}


def color_en(escala: str, t: float) -> str:
    """Color de la escala en t ∈ [0, 1] (interpolación lineal en RGB)."""
    pares = ESCALAS[escala]["colores"]
    t = min(1.0, max(0.0, t))
    for (t0, c0), (t1, c1) in zip(pares, pares[1:]):
        if t <= t1:
            f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
            b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
            return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(a, b))
    return pares[-1][1]


def rango_color(rents_pct: list[float]) -> float:
    """Límite simétrico de la escala: el percentil 90 de |r|, redondeado a un valor 'bonito'."""
    vals = sorted(abs(x) for x in rents_pct if x is not None)
    if not vals:
        return 1.0
    p = vals[int(0.9 * (len(vals) - 1))]
    for paso in (0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100):
        if p <= paso:
            return float(paso)
    return 100.0


def tam_letra(cuota: float) -> float:
    """Tamaño de la etiqueta según el peso del valor en el índice (se reduce solo si no cabe)."""
    return round(min(30.0, max(9.0, 8 + math.sqrt(cuota) * 95)), 1)


def es_cabecera(nid: str) -> bool:
    return nid == "S&P 500" or nid.startswith("sec:")


def colores_mapa(ids: list[str], valores: list[float], limite: float, escala: str = "rv") -> list[str]:
    """Colores ya resueltos: cada valor según la escala y las cabeceras en la franja oscura."""
    return [CABECERA if es_cabecera(i) else color_en(escala, 0.5 + v / (2 * limite)) for i, v in zip(ids, valores)]


def mapa_base(nodos: dict, periodo: str, por_periodo: dict, escala: str = "rv") -> go.Figure:
    pp = por_periodo[periodo]
    ids = nodos["ids"]
    # Rejilla oscura: línea fina entre valores y más gruesa alrededor de cada sector.
    bordes = [0 if i == "S&P 500" else 2.5 if i.startswith("sec:") else 1 for i in ids]
    # Las etiquetas de los valores (ticker, logo y variación) las pone el navegador encima del mapa,
    # a la medida de cada casilla; aquí sólo se dibujan las cabeceras de sector, en versalitas blancas.
    tam = [11 if es_cabecera(i) else t for i, t in zip(ids, nodos["tam_letra"])]
    etiquetas = [l.upper() if es_cabecera(i) else l for i, l in zip(ids, pp["labels"])]
    fig = go.Figure(go.Treemap(
        ids=ids, labels=etiquetas, parents=nodos["parents"],
        values=nodos["valores_cap"], branchvalues="total",
        customdata=nodos["customdata"],
        text=pp["text"],
        texttemplate=nodos["texttemplate"],
        hovertemplate=nodos["hovertemplate"],
        textposition="middle center",
        textfont=dict(family=FUENTE_MAPA, size=tam, weight=[600 if es_cabecera(i) else 700 for i in ids],
                      color=[TEXTO_CABECERA if es_cabecera(i) else "rgba(0,0,0,0)" for i in ids]),
        insidetextfont=dict(family=FUENTE_MAPA),
        marker=dict(
            colors=colores_mapa(ids, pp["colores"], pp["limite"], escala),
            line=dict(color=REJILLA, width=bordes), cornerradius=0,
            pad=dict(t=17, l=1, r=1, b=1),
        ),
        pathbar=dict(visible=True, side="top", thickness=20, edgeshape=">",
                     textfont=dict(family=FUENTE_MAPA, size=11, color=TINTA)),
        tiling=dict(packing="squarify", pad=0),
        maxdepth=3, sort=True, root=dict(color=CABECERA),
        hoverlabel=dict(bgcolor=PAPEL, bordercolor=TINTA, font=dict(family=FUENTE_MAPA, size=13, color=TINTA)),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE_MAPA, color=TINTA), separators=",.",
    )
    return fig


def barras_sectores(filas: list[dict], indice: float | None, periodo_largo: str, escala: str = "rv") -> go.Figure:
    """filas: [{nombre, r (tanto por uno), suben, total}] — orden de menor a mayor."""
    neg = color_en(escala, 0.1)
    pos = color_en(escala, 0.9)
    xs = [f["r"] * 100 for f in filas]
    fig = go.Figure(go.Bar(
        x=xs, y=[f["nombre"] for f in filas], orientation="h",
        marker=dict(color=[pos if x >= 0 else neg for x in xs], line=dict(width=0)),
        text=[F.pct(f["r"]) for f in filas], textposition="outside", cliponaxis=False,
        textfont=dict(family=FUENTE, size=13, color=TINTA),
        customdata=[[f["suben"], f["total"], F.pct(f["r"])] for f in filas],
        hovertemplate="<b>%{y}</b><br>%{customdata[2]} " + periodo_largo +
                      "<br>Suben %{customdata[0]} de %{customdata[1]}<extra></extra>",
        width=0.62,
    ))
    lim = max([abs(x) for x in xs] + [abs(indice * 100) if indice is not None else 0, 0.1])
    fig.update_xaxes(range=[-lim * 1.38 if min(xs) < 0 else -lim * 0.06, lim * 1.38 if max(xs) > 0 else lim * 0.06],
                     ticksuffix=" %", zeroline=True, zerolinecolor=TINTA, zerolinewidth=1,
                     showgrid=True, gridcolor="#ececec", tickfont=dict(size=12, color=GRIS), fixedrange=True)
    fig.update_yaxes(tickfont=dict(size=13.5, color=TINTA), fixedrange=True, ticks="", automargin=True)
    if indice is not None:
        fig.add_vline(x=indice * 100, line=dict(color=TINTA, width=1, dash="dot"))
        fig.add_annotation(x=indice * 100, y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                           text=f"S&P 500 {F.pct(indice)}", font=dict(size=12, color=GRIS, family=FUENTE))
    fig.update_layout(
        height=420, margin=dict(l=8, r=8, t=26, b=24), bargap=0.3,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE, color=TINTA), separators=",.", showlegend=False,
        hoverlabel=dict(bgcolor=PAPEL, bordercolor=TINTA, font=dict(family=FUENTE, size=13, color=TINTA)),
    )
    return fig


def distribucion(rents: list[float], periodo_largo: str, escala: str = "rv") -> go.Figure:
    """Histograma de las rentabilidades de todos los valores, con el cero marcado."""
    xs = sorted(r * 100 for r in rents)
    if not xs:
        return go.Figure()
    lo, hi = xs[int(0.01 * (len(xs) - 1))], xs[int(0.99 * (len(xs) - 1))]
    ancho = max((hi - lo) / 36, 0.05)
    # Contenedores alineados con el cero para que ninguno mezcle subidas y bajadas.
    inicio = math.floor(lo / ancho) * ancho
    n = int(math.ceil((hi - inicio) / ancho)) + 1
    bordes = [inicio + i * ancho for i in range(n + 1)]
    cuentas = [0] * n
    for x in xs:
        i = min(n - 1, max(0, int((x - inicio) // ancho)))
        cuentas[i] += 1
    centros = [(bordes[i] + bordes[i + 1]) / 2 for i in range(n)]
    lim = max(abs(lo), abs(hi)) or 1
    colores = [color_en(escala, 0.5 + 0.5 * max(-1, min(1, c / lim))) for c in centros]
    fig = go.Figure(go.Bar(
        x=centros, y=cuentas, width=[ancho * 0.92] * n,
        marker=dict(color=colores, line=dict(color="rgba(26,26,26,.35)", width=0.6)),
        customdata=[[F.pct(bordes[i] / 100, 1), F.pct(bordes[i + 1] / 100, 1)] for i in range(n)],
        hovertemplate="%{y} valores entre %{customdata[0]} y %{customdata[1]}<extra></extra>",
    ))
    mediana = xs[len(xs) // 2]
    fig.add_vline(x=0, line=dict(color=TINTA, width=1))
    fig.add_vline(x=mediana, line=dict(color=TINTA, width=1, dash="dot"))
    fig.add_annotation(x=mediana, y=1, yref="paper", yanchor="bottom", showarrow=False,
                       text=f"mediana {F.pct(mediana / 100)}", font=dict(size=12, color=GRIS, family=FUENTE))
    fig.update_xaxes(ticksuffix=" %", showgrid=False, tickfont=dict(size=12, color=GRIS), fixedrange=True,
                     title=dict(text=f"Rentabilidad {periodo_largo}", font=dict(size=12.5, color=GRIS)))
    fig.update_yaxes(showgrid=True, gridcolor="#ececec", tickfont=dict(size=12, color=GRIS), fixedrange=True,
                     title=dict(text="Número de valores", font=dict(size=12.5, color=GRIS)))
    fig.update_layout(
        height=300, margin=dict(l=8, r=8, t=26, b=8), bargap=0,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE, color=TINTA), separators=",.", showlegend=False,
        hoverlabel=dict(bgcolor=PAPEL, bordercolor=TINTA, font=dict(family=FUENTE, size=13, color=TINTA)),
    )
    return fig
