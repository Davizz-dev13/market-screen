/* Market Screen · el pegamento del navegador.
   Las figuras y todos los números ya vienen hechos de Python (datos.json);
   aquí sólo se dibujan y se intercambian al cambiar periodo, grupo, tamaño o colores. */
(function () {
  'use strict';
  var D, estado = { p: '1D', g: '', tam: 'cap', esc: 'rv' }, nivel = 'S&P 500', idsSector = [];
  var CONF = { displayModeBar: false, responsive: true, locale: 'es' };
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };

  function clase(r) { return r > 0 ? 'pos' : r < 0 ? 'neg' : ''; }
  function svgSpark(v, alto) {
    if (!v.sp) return '';
    var r = v.r['1A'], col = r == null ? '#555' : r >= 0 ? 'var(--green)' : 'var(--red)';
    return '<svg viewBox="0 -2 100 36" preserveAspectRatio="none" aria-hidden="true"' + (alto ? ' style="height:' + alto + 'px"' : '') +
      '><path d="' + v.sp + '" fill="none" stroke="' + col + '" stroke-width="1.4" vector-effect="non-scaling-stroke"/></svg>';
  }

  function mapa() {
    var pp = D.mapa.por_periodo[estado.p], e = D.escalas[estado.esc];
    Plotly.restyle('mapa', {
      'marker.colors': [pp.colores], text: [pp.text], labels: [pp.labels], 'marker.cmin': -pp.limite, 'marker.cmax': pp.limite,
      'marker.colorscale': [e.colores],
      values: [estado.tam === 'cap' ? D.mapa.figura.data[0].values : D.mapa.valores_igual]
    });
    $('ley-min').textContent = pp.leyenda[0];
    $('ley-max').textContent = pp.leyenda[2];
    $('ley-barra').style.background = 'linear-gradient(90deg,' + e.colores.map(function (c) { return c[1] + ' ' + (c[0] * 100) + '%'; }).join(',') + ')';
  }

  function graficos() {
    ['barras', 'distribucion'].forEach(function (k) {
      var f = D[k][estado.esc][estado.p];
      Plotly.react(k, f.data, f.layout, CONF);
    });
  }

  function resumen() {
    var r = D.resumen[estado.p];
    var ki = $('k-indice'); ki.textContent = r.indice; ki.className = r.indice_signo ? 'pos' : 'neg';
    $('k-suben').textContent = r.suben; $('k-bajan').textContent = r.bajan;
    $('k-mejor').textContent = r.mejor ? r.mejor[0] + ' ' + r.mejor[1] : '—';
    $('k-peor').textContent = r.peor ? r.peor[0] + ' ' + r.peor[1] : '—';
  }

  function listas() {
    var p = estado.p, g = estado.g;
    var vs = D.valores.filter(function (v) { return v.r[p] != null && (g === '' || v.s === +g); });
    vs.sort(function (a, b) { return b.r[p] - a.r[p]; });
    var arriba = vs.filter(function (v) { return v.r[p] > 0; }).slice(0, 10);
    var abajo = vs.filter(function (v) { return v.r[p] < 0; }).reverse().slice(0, 10);
    [['suben', arriba, 'Ninguno sube en este periodo.'], ['bajan', abajo, 'Ninguno baja en este periodo.']].forEach(function (x) {
      var h = x[1].map(function (v) {
        return '<tr data-t="' + esc(v.t) + '" tabindex="0"><td class="tk">' + esc(v.t) + '</td><td class="nm">' + esc(v.n) +
          '</td><td class="sp">' + svgSpark(v) + '</td><td class="num ' + clase(v.r[p]) + '">' + esc(v.rt[p]) + '</td></tr>';
      }).join('');
      $(x[0]).innerHTML = '<tbody>' + (h || '<tr><td class="vacio" colspan="4">' + x[2] + '</td></tr>') + '</tbody>';
    });
  }

  function ficha(t) {
    var v = D.valores.find(function (x) { return x.t === t; });
    if (!v) return;
    var total = D.valores.reduce(function (a, x) { return a + x.cap; }, 0);
    var peso = (v.cap / total * 100).toFixed(2).replace('.', ',') + ' %';
    var rets = D.periodos.map(function (p) {
      var r = v.r[p.id];
      return '<div class="' + (p.id === estado.p ? 'on' : '') + '"><span>' + p.corto + '</span><b class="' + clase(r) + '">' + (v.rt[p.id] || '—') + '</b></div>';
    }).join('');
    var f = $('ficha');
    f.innerHTML = '<button type="button" class="cerrar" aria-label="Cerrar ficha">×</button>' +
      '<h3>' + esc(v.n) + ' <span class="tag">' + esc(v.t) + '</span></h3>' +
      '<p class="meta">' + esc(D.sectores[v.s]) + ' · ' + esc(v.sub) + '</p>' +
      '<div class="linea"><div class="dato"><span class="k">Precio</span><b>' + esc(v.p) + '</b></div>' +
      '<div class="dato"><span class="k">Capitalización</span><b>' + esc(v.c) + '</b></div>' +
      '<div class="dato"><span class="k">Peso en el S&amp;P 500</span><b>' + peso + '</b></div></div>' +
      '<div class="rets">' + rets + '</div>' + svgSpark(v, 120) +
      '<p class="pie">Último año, cierres diarios. Fuente: Yahoo Finance.</p>';
    f.hidden = false;
    f.querySelector('.cerrar').addEventListener('click', function () { f.hidden = true; });
    f.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function todo() { mapa(); graficos(); resumen(); listas(); }

  function controles() {
    document.querySelectorAll('#periodos button').forEach(function (b) {
      b.addEventListener('click', function () {
        estado.p = b.dataset.p;
        document.querySelectorAll('#periodos button').forEach(function (x) {
          x.classList.toggle('active', x === b); x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
        });
        todo();
        var f = $('ficha'); if (!f.hidden) { var t = f.querySelector('.tag'); if (t) ficha(t.textContent); }
      });
    });
    $('grupo').addEventListener('change', function (e) {
      estado.g = e.target.value;
      nivel = estado.g === '' ? 'S&P 500' : idsSector[+estado.g];
      Plotly.restyle('mapa', { level: nivel });
      listas();
    });
    $('tamano').addEventListener('change', function (e) { estado.tam = e.target.value; mapa(); });
    $('escala').addEventListener('change', function (e) { estado.esc = e.target.value; mapa(); graficos(); });
    ['suben', 'bajan'].forEach(function (id) {
      $(id).addEventListener('click', function (e) { var tr = e.target.closest('tr[data-t]'); if (tr) ficha(tr.dataset.t); });
      $(id).addEventListener('keydown', function (e) { var tr = e.target.closest('tr[data-t]'); if (tr && e.key === 'Enter') ficha(tr.dataset.t); });
    });
    $('lista-valores').innerHTML = D.valores.map(function (v) { return '<option value="' + esc(v.t) + ' · ' + esc(v.n) + '">'; }).join('');
    $('buscar').addEventListener('change', function (e) {
      var q = e.target.value.trim().toUpperCase(), t = q.split(' · ')[0];
      var v = D.valores.find(function (x) { return x.t === t; }) ||
        D.valores.find(function (x) { return x.n.toUpperCase().indexOf(q) === 0; }) ||
        D.valores.find(function (x) { return x.n.toUpperCase().indexOf(q) >= 0; });
      if (v) ficha(v.t);
    });
  }

  function iniciar() {
    var fig = D.mapa.figura;
    idsSector = fig.data[0].ids.filter(function (id) { return id.indexOf('sec:') === 0; });
    $('mapa').innerHTML = '';
    Plotly.newPlot('mapa', fig.data, fig.layout, CONF).then(function (gd) {
      gd.on('plotly_treemapclick', function (ev) {
        var pt = ev.points[0], id = pt.id;
        if (id !== 'S&P 500' && id.indexOf('sec:') !== 0) { ficha(id); return false; }
        // Sincroniza el selector de grupo con el zoom del propio mapa.
        if (id === nivel || id === 'S&P 500') { nivel = id === nivel && id !== 'S&P 500' ? 'S&P 500' : id; }
        else { nivel = id; }
        var i = idsSector.indexOf(nivel);
        estado.g = i < 0 ? '' : String(i);
        $('grupo').value = estado.g;
        listas();
      });
    });
    controles();
    todo();
  }

  document.addEventListener('DOMContentLoaded', function () {
    fetch('datos.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (d) {
      D = d;
      $('sello').textContent = d.sello;
      (function esperar() { if (window.Plotly) iniciar(); else setTimeout(esperar, 50); })();
    }).catch(function () {
      $('mapa').innerHTML = '<p class="ms-cargando">No se han podido cargar los datos. Prueba a recargar la página.</p>';
    });
  });
})();
