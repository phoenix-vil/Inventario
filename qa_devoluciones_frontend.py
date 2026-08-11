#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] FRONTEND de devoluciones:
 - Crea static/devoluciones.html
 - Registra la ruta /devoluciones en main.py
 - Agrega el tile en el menu principal (solo gerentes)
Uso: cd ~/inventario-qa && python3 qa_devoluciones_frontend.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
res = []

PAGINA = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#1a1a18">
<meta name="mobile-web-app-capable" content="yes">
<link rel="icon" type="image/png" href="/static/icon-nav-v2.png" media="(prefers-color-scheme: light)">
<link rel="icon" type="image/png" href="/static/icon-nav-blanco.png" media="(prefers-color-scheme: dark)">
<link rel="apple-touch-icon" href="/static/touch-icon-v3-180.png">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Devoluciones · Only Enterprises</title>
<link rel="stylesheet" href="/static/modern.css">
<style>
.buscador{display:flex;gap:8px;margin-bottom:1.25rem}
.buscador input{flex:1;height:48px;padding:0 14px;border:0.5px solid var(--border);border-radius:10px;background:var(--bg2);color:var(--text);font-size:16px}
.buscador button{height:48px;padding:0 22px;border:none;border-radius:10px;background:var(--text);color:var(--bg2);font-weight:600;font-size:15px;cursor:pointer}
.venta-card{background:var(--bg2);border:0.5px solid var(--border);border-radius:14px;padding:1.25rem;margin-bottom:1rem}
.venta-head{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:.875rem;padding-bottom:.875rem;border-bottom:0.5px solid var(--border)}
.venta-id{font-size:18px;font-weight:700}
.venta-meta{font-size:12px;color:var(--text2);margin-top:2px}
.badge{display:inline-block;padding:3px 10px;border-radius:100px;font-size:11px;font-weight:700}
.badge-activa{background:var(--green-bg);color:var(--green)}
.badge-parcial{background:var(--amber-bg);color:var(--amber)}
.badge-cancelada{background:var(--red-bg);color:var(--red)}
.item-row{display:flex;align-items:center;gap:10px;padding:.75rem 0;border-bottom:0.5px solid var(--border)}
.item-row:last-child{border-bottom:none}
.item-info{flex:1;min-width:0}
.item-nombre{font-size:14px;font-weight:600}
.item-sub{font-size:12px;color:var(--text2);margin-top:2px}
.item-cant{width:78px;height:40px;padding:0 8px;border:0.5px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:15px;text-align:center}
.item-cant:disabled{opacity:.4}
.totales{margin-top:1rem;padding-top:.875rem;border-top:0.5px solid var(--border)}
.total-line{display:flex;justify-content:space-between;margin-bottom:5px;font-size:14px}
.total-line.grande{font-size:17px;font-weight:700;margin-top:8px}
.acciones{display:flex;gap:8px;margin-top:1.25rem;flex-wrap:wrap}
.btn-devolver{flex:1;min-width:180px;height:48px;border:none;border-radius:10px;background:var(--amber);color:#fff;font-weight:700;font-size:15px;cursor:pointer}
.btn-cancelar-venta{flex:1;min-width:180px;height:48px;border:0.5px solid var(--red);border-radius:10px;background:var(--red-bg);color:var(--red);font-weight:700;font-size:15px;cursor:pointer}
.btn-devolver:disabled,.btn-cancelar-venta:disabled{opacity:.4;cursor:not-allowed}
.hist-dev{margin-top:1rem;padding:.875rem;background:var(--bg);border-radius:10px}
.hist-dev-title{font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.hist-dev-item{font-size:12px;color:var(--text2);margin-bottom:4px}
.vacio{text-align:center;padding:3rem 1rem;color:var(--text2)}
</style>
</head>
<body>

<div class="topbar">
  <a href="/" class="btn-inicio" title="Inicio"><img src="/static/icon-nav-v2.png" alt="Inicio" class="nav-icon" style="height:32px;width:32px"></a>
  <h1 class="topbar-title">↩️ Devoluciones</h1>
  <div class="topbar-right"></div>
</div>

<div class="container">
  <div class="buscador">
    <input type="number" id="num-ticket" placeholder="Número de ticket (ej. 95)" inputmode="numeric" onkeydown="if(event.key==='Enter')buscarVenta()">
    <button onclick="buscarVenta()">Buscar</button>
  </div>

  <div class="msg" id="msg-general"></div>
  <div id="resultado"></div>
</div>

<!-- Modal de motivo -->
<div class="overlay" id="motivo-modal">
  <div class="modal">
    <h2 id="motivo-titulo">Motivo</h2>
    <p id="motivo-resumen" style="font-size:13px;color:var(--text2);margin-bottom:12px"></p>
    <div class="field"><label>Motivo (obligatorio)</label><input type="text" id="motivo-input" placeholder="Ej: producto defectuoso" autocomplete="off"></div>
    <div class="msg" id="motivo-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarMotivo()">Cancelar</button>
      <button class="primary" onclick="confirmarMotivo()">Confirmar</button>
    </div>
  </div>
</div>

<script src="/static/auth.js"></script>
<script>
requireGerente();

function money(n){return '$'+Number(n||0).toLocaleString('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2});}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}

let ventaActual = null;
let accionPendiente = null;

function mostrarMsg(texto, tipo){
  const el = document.getElementById('msg-general');
  el.className = 'msg ' + (tipo||'error') + ' show';
  el.textContent = texto;
}
function limpiarMsg(){ document.getElementById('msg-general').className = 'msg'; }

async function buscarVenta(){
  const id = document.getElementById('num-ticket').value.trim();
  limpiarMsg();
  document.getElementById('resultado').innerHTML = '';
  ventaActual = null;
  if(!id){ mostrarMsg('Escribe el número de ticket'); return; }

  try{
    const r = await authFetch('/api/ventas/' + id);
    if(r.status === 404){ mostrarMsg('No existe una venta con el ticket #' + id); return; }
    if(!r.ok){ mostrarMsg('No se pudo consultar la venta'); return; }
    ventaActual = await r.json();
    renderVenta();
  }catch(e){ mostrarMsg('Error de conexión'); }
}

function devueltoPorProducto(){
  const mapa = {};
  (ventaActual.devoluciones || []).forEach(function(d){
    mapa[d.producto_id] = (mapa[d.producto_id] || 0) + d.cantidad;
  });
  return mapa;
}

function renderVenta(){
  const v = ventaActual;
  const estado = v.estado || 'activa';
  const yaDev = devueltoPorProducto();
  const fecha = new Date(v.fecha).toLocaleString('es-MX').replace(',', '');
  const nombresMet = {efectivo:'Efectivo', tarjeta:'Tarjeta', credito:'Crédito', transferencia:'Transferencia'};
  const etiquetasEstado = {activa:'Activa', parcial:'Devolución parcial', cancelada:'Cancelada'};

  let html = '<div class="venta-card">';
  html += '<div class="venta-head"><div>'
    + '<div class="venta-id">Ticket #' + v.id + '</div>'
    + '<div class="venta-meta">' + fecha + '</div>'
    + '<div class="venta-meta">' + esc(v.sucursal || '') + (v.operador ? ' · ' + esc(v.operador) : '') + '</div>'
    + '<div class="venta-meta">Pago: ' + (nombresMet[v.metodo_pago] || v.metodo_pago) + '</div>'
    + '</div>'
    + '<span class="badge badge-' + estado + '">' + (etiquetasEstado[estado] || estado) + '</span>'
    + '</div>';

  const cancelada = estado === 'cancelada';

  (v.detalle || []).forEach(function(it){
    const dev = yaDev[it.producto_id] || 0;
    const disp = Math.round((it.cantidad - dev) * 1000) / 1000;
    html += '<div class="item-row">'
      + '<div class="item-info">'
      + '<div class="item-nombre">' + esc(it.nombre) + '</div>'
      + '<div class="item-sub">' + it.cantidad + ' x ' + money(it.precio_unitario)
      + (dev > 0 ? ' · <span style="color:var(--amber)">' + dev + ' devuelto(s)</span>' : '')
      + '</div></div>'
      + '<input type="number" class="item-cant" id="dev-' + it.producto_id + '" min="0" max="' + disp + '" step="any" placeholder="0"'
      + (disp <= 0 || cancelada ? ' disabled' : '') + '>'
      + '</div>';
  });

  const neto = v.total - (v.total_devuelto || 0);
  html += '<div class="totales">';
  html += '<div class="total-line"><span>Total original</span><span>' + money(v.total) + '</span></div>';
  if(v.total_devuelto > 0){
    html += '<div class="total-line" style="color:var(--red)"><span>Devuelto</span><span>-' + money(v.total_devuelto) + '</span></div>';
  }
  html += '<div class="total-line grande"><span>Neto</span><span>' + money(neto) + '</span></div>';
  html += '</div>';

  html += '<div class="acciones">'
    + '<button class="btn-devolver" onclick="pedirMotivoDevolucion()"' + (cancelada ? ' disabled' : '') + '>Devolver seleccionados</button>'
    + '<button class="btn-cancelar-venta" onclick="pedirMotivoCancelacion()"' + (cancelada ? ' disabled' : '') + '>Cancelar venta completa</button>'
    + '</div>';

  if((v.devoluciones || []).length){
    html += '<div class="hist-dev"><div class="hist-dev-title">Devoluciones registradas</div>';
    v.devoluciones.forEach(function(d){
      const f = new Date(d.fecha).toLocaleString('es-MX').replace(',', '');
      html += '<div class="hist-dev-item">• ' + d.cantidad + ' x ' + esc(d.nombre) + ' — ' + money(d.importe)
        + '<br><span style="opacity:.8">' + f + ' · ' + esc(d.operador || '')
        + (d.motivo ? ' · ' + esc(d.motivo) : '') + '</span></div>';
    });
    html += '</div>';
  }

  html += '</div>';
  document.getElementById('resultado').innerHTML = html;
}

function recolectarItems(){
  const items = [];
  (ventaActual.detalle || []).forEach(function(it){
    const el = document.getElementById('dev-' + it.producto_id);
    if(!el || el.disabled) return;
    const cant = parseFloat(el.value);
    if(!isNaN(cant) && cant > 0){
      items.push({producto_id: it.producto_id, cantidad: cant});
    }
  });
  return items;
}

function pedirMotivoDevolucion(){
  limpiarMsg();
  const items = recolectarItems();
  if(!items.length){ mostrarMsg('Escribe la cantidad a devolver en al menos un artículo'); return; }
  const total = items.reduce(function(s, i){
    const linea = ventaActual.detalle.find(function(x){ return x.producto_id === i.producto_id; });
    return s + (linea ? linea.precio_unitario * i.cantidad : 0);
  }, 0);
  accionPendiente = {tipo: 'devolucion', items: items};
  abrirMotivo('Devolver artículos',
    items.length + ' artículo(s) · Se reembolsarán ' + money(total));
}

function pedirMotivoCancelacion(){
  limpiarMsg();
  const neto = ventaActual.total - (ventaActual.total_devuelto || 0);
  accionPendiente = {tipo: 'cancelacion'};
  abrirMotivo('Cancelar venta completa',
    'Se devolverá todo lo pendiente del ticket #' + ventaActual.id + ' · ' + money(neto));
}

function abrirMotivo(titulo, resumen){
  document.getElementById('motivo-titulo').textContent = titulo;
  document.getElementById('motivo-resumen').textContent = resumen;
  document.getElementById('motivo-input').value = '';
  document.getElementById('motivo-msg').className = 'msg';
  document.getElementById('motivo-modal').classList.add('open');
  setTimeout(function(){ document.getElementById('motivo-input').focus(); }, 60);
}
function cerrarMotivo(){
  document.getElementById('motivo-modal').classList.remove('open');
  accionPendiente = null;
}

async function confirmarMotivo(){
  const motivo = document.getElementById('motivo-input').value.trim();
  const msg = document.getElementById('motivo-msg');
  if(!motivo){ msg.className = 'msg error show'; msg.textContent = 'El motivo es obligatorio'; return; }
  if(!accionPendiente){ cerrarMotivo(); return; }

  const esDevolucion = accionPendiente.tipo === 'devolucion';
  const url = '/api/ventas/' + ventaActual.id + (esDevolucion ? '/devolucion' : '/cancelar');
  const cuerpo = esDevolucion ? {items: accionPendiente.items, motivo: motivo} : {motivo: motivo};

  try{
    const r = await authFetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(cuerpo),
    });
    const data = await r.json();
    if(!r.ok){
      msg.className = 'msg error show';
      msg.textContent = extraerMensaje(data.detail, 'No se pudo completar la operación');
      return;
    }
    cerrarMotivo();
    const el = document.getElementById('msg-general');
    el.className = 'msg success show';
    el.textContent = (esDevolucion ? 'Devolución registrada: ' : 'Venta cancelada: ')
      + money(data.monto_devuelto) + ' · Stock actualizado';
    document.getElementById('num-ticket').value = ventaActual.id;
    buscarVentaSilencioso();
  }catch(e){
    msg.className = 'msg error show';
    msg.textContent = 'Error de conexión';
  }
}

async function buscarVentaSilencioso(){
  try{
    const r = await authFetch('/api/ventas/' + ventaActual.id);
    if(r.ok){ ventaActual = await r.json(); renderVenta(); }
  }catch(e){}
}

function extraerMensaje(detail, fallback){
  if(!detail) return fallback;
  if(typeof detail === 'string') return detail;
  if(Array.isArray(detail)){
    return detail.map(function(e){ return (e && e.msg) ? e.msg : JSON.stringify(e); }).join(' — ');
  }
  return fallback;
}
</script>
</body>
</html>
"""

# ── 1. Crear la pagina ─────────────────────────────────────
ruta = os.path.join(QA, 'static', 'devoluciones.html')
open(ruta, 'w', encoding='utf-8').write(PAGINA)
res.append("OK static/devoluciones.html creada (" + str(len(PAGINA)) + " bytes)")

# ── 2. Registrar la ruta en main.py ────────────────────────
ruta_main = os.path.join(QA, 'main.py')
src = open(ruta_main, encoding='utf-8').read()

if '@app.get("/devoluciones"' in src:
    res.append("* main.py: la ruta /devoluciones ya existia")
else:
    viejo = '''@app.get("/historial", response_class=FileResponse)
def historial_page():
    return FileResponse("static/historial.html")'''
    nuevo = '''@app.get("/historial", response_class=FileResponse)
def historial_page():
    return FileResponse("static/historial.html")


@app.get("/devoluciones", response_class=FileResponse)
def devoluciones_page():
    return FileResponse("static/devoluciones.html")'''
    if viejo in src:
        src = src.replace(viejo, nuevo, 1)
        open(ruta_main, 'w', encoding='utf-8').write(src)
        res.append("OK main.py: ruta /devoluciones registrada")
    else:
        res.append("ERROR main.py: no se encontro la ruta /historial como referencia")

# ── 3. Agregar el tile al menu ─────────────────────────────
ruta_menu = os.path.join(QA, 'static', 'menu.html')
src = open(ruta_menu, encoding='utf-8').read()

if 'href="/devoluciones"' in src:
    res.append("* menu.html: el tile ya existia")
else:
    viejo_tile = '''  <a class="menu-btn solo-gerente" href="/historial" style="display:none">
    <div class="icon icon-precios">\U0001F4CB</div>
    <div class="menu-text">
      <div class="menu-title">Historial de ventas</div>
      <div class="menu-desc">Consulta y descarga tus ventas</div>
    </div>
    <div class="arrow">\u203A</div>
  </a>'''
    nuevo_tile = viejo_tile + '''

  <a class="menu-btn solo-gerente" href="/devoluciones" style="display:none">
    <div class="icon icon-precios">\u21A9\uFE0F</div>
    <div class="menu-text">
      <div class="menu-title">Devoluciones</div>
      <div class="menu-desc">Devolver artículos o cancelar una venta</div>
    </div>
    <div class="arrow">\u203A</div>
  </a>'''
    if viejo_tile in src:
        src = src.replace(viejo_tile, nuevo_tile, 1)
        open(ruta_menu, 'w', encoding='utf-8').write(src)
        res.append("OK menu.html: tile de Devoluciones agregado")
    else:
        res.append("ERROR menu.html: no se encontro el tile de Historial como referencia")

# ── Resultados ─────────────────────────────────────────────
print()
for r in res:
    print(r)

print()
ok = True
for f in ['devoluciones.html', 'menu.html']:
    p = os.path.join(QA, 'static', f)
    s = open(p, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    b = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + f + ":", "OK" if b else "DESBALANCEADO")
    if not b:
        ok = False

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Entra a QA como GERENTE y abre 'Devoluciones' en el menu.")
else:
    print("Hubo errores o desbalance. NO se reinicio el servicio.")
