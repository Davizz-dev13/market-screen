# Market Screen

El S&P 500 de un vistazo, en Python. Forma parte de [Sharpe Lab](https://davizz-dev13.github.io/sharpe-lab/).

**Web:** https://davizz-dev13.github.io/market-screen/

- **Mapa por sectores**: las ~500 empresas agrupadas por sector GICS; el tamaño de cada casilla es su capitalización y el color, la rentabilidad del periodo. Toca un sector para ampliarlo y un valor para ver su ficha.
- **Periodos**: 1 día, 1 semana, 1 mes, 3 meses, en lo que va de año (YTD) y 1 año.
- **Controles**: grupo (sector), tamaño (por capitalización o todas iguales) y dos escalas de color (rojo-verde y naranja-azul, apta para daltónicos).
- **Rentabilidad por sector** (media ponderada por capitalización, con el S&P 500 como referencia), **distribución** de las rentabilidades de todos los valores, **los que más suben y más bajan** con su minigráfico del último año y **buscador** con ficha de cada valor.

## Datos

| Qué | De dónde |
| --- | --- |
| Componentes y sector GICS | [List of S&P 500 companies](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) (Wikipedia) |
| Precio, cierre anterior y capitalización | Yahoo Finance (`v7/finance/quote`) |
| Cierres diarios de los dos últimos años | Yahoo Finance (`v8/finance/spark`) |

Yahoo bloquea con un 429 las peticiones que no parecen de un navegador, así que se usa [`curl_cffi`](https://github.com/lexiforest/curl_cffi) haciéndose pasar por Chrome. Si un valor no trae datos se omite y se apunta en el log de la Action: nunca se rellena un número. Si llegan menos de 450 valores, la Action falla a propósito y la web se queda como estaba.

Notas de cálculo:

- Las rentabilidades son de precio (sin dividendos). La base de cada periodo es el último cierre en o antes de la fecha de referencia (hace 7 días, 1 mes, 3 meses, 31 de diciembre del año anterior o hace 1 año).
- El "S&P 500" y los sectores son medias ponderadas por capitalización total (cap actual / cap al inicio − 1). Es una aproximación: el índice oficial pondera por capital flotante.
- Alphabet, Fox y News Corp cotizan con dos clases; Yahoo da la capitalización de toda la empresa en cada una, así que se muestra una sola clase (la A) para no contarlas dos veces.

## Actualización

La Action [`actualizar.yml`](.github/workflows/actualizar.yml) se ejecuta de lunes a viernes a las 15:00, 18:30 y 21:30 UTC (dos veces con el mercado de Nueva York abierto y otra tras el cierre), además de con cada push a `main` y a mano desde la pestaña *Actions* (*Run workflow*). Descarga los datos, pasa las pruebas, genera la web y la publica en GitHub Pages. No hace commits: los datos viven en la web publicada (`datos.json`).

## Ejecutarlo en local

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
python -m pytest -q
python build.py                      # descarga los datos y genera _site/
python -m http.server -d _site 8000  # abre http://localhost:8000
```

`python build.py --cache crudo.json` guarda la descarga la primera vez y la reutiliza después: útil para retocar el diseño sin volver a pedir los datos.

## Estructura

```
build.py                  orquesta todo: descarga, cálculos, figuras y página
marketscreen/fuentes.py   Wikipedia + Yahoo Finance (curl_cffi)
marketscreen/calculos.py  rentabilidades, agregados por sector y minigráficos
marketscreen/graficos.py  figuras de Plotly (mapa, sectores, distribución) y escalas de color
marketscreen/formato.py   números a la española
plantillas/index.html     plantilla Jinja de la página
estatico/                 CSS, el JavaScript mínimo que conecta los controles y el favicon
tests/                    pruebas (pytest)
```

Las figuras se diseñan en Python con Plotly y se guardan en `datos.json`; el navegador sólo las dibuja con Plotly.js y, al cambiar de periodo o de grupo, intercambia los arrays ya calculados. El estilo (tipografía, barra superior y pie) es el de Sharpe Lab.

*Proyecto personal de aprendizaje. Nada de esto es asesoramiento financiero.*
