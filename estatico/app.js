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

  // ── Colores del mapa: se resuelven aquí (como en graficos.py) para que las cabeceras de sector
  //    sean una franja oscura y cada valor lleve su color exacto de la escala. ──
  var CABECERA = '#141414';
  function esCabecera(id) { return id === 'S&P 500' || id.indexOf('sec:') === 0; }
  function hex2rgb(h) { return [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function colorEn(pares, t) {
    t = Math.min(1, Math.max(0, t));
    for (var k = 0; k < pares.length - 1; k++) {
      var t0 = pares[k][0], t1 = pares[k + 1][0];
      if (t <= t1) {
        var f = t1 === t0 ? 0 : (t - t0) / (t1 - t0), a = hex2rgb(pares[k][1]), b = hex2rgb(pares[k + 1][1]);
        return '#' + a.map(function (x, i) { return ('0' + Math.round(x + (b[i] - x) * f).toString(16)).slice(-2); }).join('');
      }
    }
    return pares[pares.length - 1][1];
  }

  function mapa() {
    var pp = D.mapa.por_periodo[estado.p], e = D.escalas[estado.esc], ids = D.mapa.figura.data[0].ids;
    var colores = ids.map(function (id, i) { return esCabecera(id) ? CABECERA : colorEn(e.colores, 0.5 + pp.colores[i] / (2 * pp.limite)); });
    var etiquetas = ids.map(function (id, i) { return esCabecera(id) ? pp.labels[i].toUpperCase() : pp.labels[i]; });
    Plotly.restyle('mapa', {
      'marker.colors': [colores], text: [pp.text], labels: [etiquetas],
      values: [estado.tam === 'cap' ? D.mapa.figura.data[0].values : D.mapa.valores_igual]
    });
    $('ley-min').textContent = pp.leyenda[0];
    $('ley-max').textContent = pp.leyenda[2];
    $('ley-barra').style.background = 'linear-gradient(90deg,' + e.colores.map(function (c) { return c[1] + ' ' + (c[0] * 100) + '%'; }).join(',') + ')';
  }

  // ── Etiquetas de las casillas: logo, ticker y variación, en HTML encima del mapa y a la medida de
  //    cada casilla (Plotly dibuja la rejilla, los colores y las cabeceras; el texto de los valores es
  //    transparente). Se recalculan cada vez que Plotly termina de dibujar. ──
  var capa = null, idx = {};
  function luz(rgb) {
    var m = String(rgb).match(/\d+(\.\d+)?/g); if (!m) return 0;
    var c = m.slice(0, 3).map(function (v) { v = v / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function etiquetas() {
    var gd = $('mapa'), cont = gd.querySelector('.svg-container');
    if (!cont) return;
    if (!capa || !cont.contains(capa)) {
      capa = document.createElement('div'); capa.className = 'ms-ov'; capa.setAttribute('aria-hidden', 'true');
      var svgs = cont.querySelectorAll('svg.main-svg');
      cont.insertBefore(capa, svgs.length > 1 ? svgs[svgs.length - 1] : null);  // debajo de la capa del tooltip
    }
    var pp = D.mapa.por_periodo[estado.p], base = cont.getBoundingClientRect(), logos = D.logos || {}, h = [];
    gd.querySelectorAll('.treemaplayer g.slice').forEach(function (g) {
      var d = g.__data__, id = d && d.data && d.data.data && d.data.data.id;
      if (!id || esCabecera(id) || idx[id] == null) return;
      var p = g.querySelector('path.surface'); if (!p) return;
      var r = p.getBoundingClientRect(), w = r.width - 4, al = r.height - 4;
      if (w < 14 || al < 9) return;
      var tk = id, pc = pp.text[idx[id]] || '', ancho = w * 0.88;
      var fsW = ancho / (Math.max(tk.length, 2) * 0.66 + 0.1);
      var anchoPc = function (s) { return ancho / (s.length * 0.58 + 0.1); };
      if (anchoPc(pc) < 8 && pc) pc = pc.replace(/\s*%$/, '');   // casilla estrecha: sin el «%»
      var fpW = anchoPc(pc), tamPc = function (f) { return Math.min(Math.max(f * 0.58, Math.min(f * 0.9, 9)), fpW); };
      // Con logo (sólo casillas holgadas): círculo arriba y el texto en lo que queda.
      var lg = 0, resto = al;
      if (logos[id] && w >= 46 && al >= 62) {
        lg = Math.round(Math.min(w * 0.3, al * 0.27, 50));
        resto = al - lg * 1.3 - 6;
      }
      var fs = Math.min(fsW, resto * 0.36, 40), fp = tamPc(fs);
      var conPc = fp >= 7.5 && resto >= fs + fp * 1.25 + 2;
      if (lg && (lg < 22 || fs < 12 || !conPc)) { lg = 0; resto = al; fs = Math.min(fsW, al * 0.36, 40); fp = tamPc(fs); conPc = fp >= 7.5 && al >= fs + fp * 1.25 + 2; }
      if (!conPc) {  // antes que quitar la variación, achica el ticker
        var fs2 = Math.min(fsW, (al - 2) / (1 + 0.58 * 1.25), 40), fp2 = tamPc(fs2);
        if (fs2 >= 9 && fp2 >= 7.5 && al >= fs2 + fp2 * 1.25 + 2) { fs = fs2; fp = fp2; conPc = true; } else fs = Math.min(fsW, al * 0.78, 40);
      }
      if (fs < 7.5) return;
      var oscuro = luz(d.color) > 0.42;
      h.push('<div class="t' + (oscuro ? ' osc' : '') + '" style="left:' + (r.left - base.left + 2).toFixed(1) + 'px;top:' + (r.top - base.top + 2).toFixed(1) +
        'px;width:' + w.toFixed(1) + 'px;height:' + al.toFixed(1) + 'px">' +
        (lg ? '<span class="lg" style="width:' + lg + 'px;height:' + lg + 'px"><img src="' + esc(logos[id]) + '" alt="" loading="lazy" decoding="async"></span>' : '') +
        '<b class="tk" style="font-size:' + fs.toFixed(1) + 'px">' + esc(tk) + '</b>' +
        (conPc ? '<b class="pc" style="font-size:' + fp.toFixed(1) + 'px">' + esc(pc) + '</b>' : '') + '</div>');
    });
    capa.innerHTML = h.join('');
    capa.classList.remove('oculta');
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
    fig.data[0].ids.forEach(function (id, i) { idx[id] = i; });
    $('mapa').innerHTML = '';
    var pendiente = 0;
    function repintar() { cancelAnimationFrame(pendiente); pendiente = requestAnimationFrame(etiquetas); }
    Plotly.newPlot('mapa', fig.data, fig.layout, CONF).then(function (gd) {
      gd.on('plotly_afterplot', repintar);
      gd.on('plotly_treemapclick', function (ev) {
        var pt = ev.points[0], id = pt.id;
        if (id !== 'S&P 500' && id.indexOf('sec:') !== 0) { ficha(id); return false; }
        if (capa) capa.classList.add('oculta');   // durante la animación del zoom
        // Sincroniza el selector de grupo con el zoom del propio mapa.
        if (id === nivel || id === 'S&P 500') { nivel = id === nivel && id !== 'S&P 500' ? 'S&P 500' : id; }
        else { nivel = id; }
        var i = idsSector.indexOf(nivel);
        estado.g = i < 0 ? '' : String(i);
        $('grupo').value = estado.g;
        listas();
      });
      gd.on('plotly_animated', repintar);
      window.addEventListener('resize', repintar);
      repintar();
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
