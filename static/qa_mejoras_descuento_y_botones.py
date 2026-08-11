#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Cambia los botones de metodo de pago a una cuadricula 2x2 (menos
amontonados con los 4 metodos).
2. Agrega un toggle %/$ en el descuento general Y en el descuento por
articulo, para poder ingresar el monto en pesos o el porcentaje.
Uso: cd ~/inventario-qa/static && python3 qa_mejoras_descuento_y_botones.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Botones de metodo de pago: grid 2x2
# ================================================================
viejo_grid = '''      <div style="display:flex;gap:8px">
        <button type="button" id="btn-efectivo" class="metodo-btn activo" onclick="setMetodo('efectivo')">💵 Efectivo</button>
        <button type="button" id="btn-tarjeta" class="metodo-btn" onclick="setMetodo('tarjeta')">💳 Tarjeta</button>
        <button type="button" id="btn-credito" class="metodo-btn" onclick="setMetodo('credito')">📒 Crédito</button>
        <button type="button" id="btn-transferencia" class="metodo-btn" onclick="setMetodo('transferencia')">🏦 Transferencia</button>
      </div>'''
nuevo_grid = '''      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <button type="button" id="btn-efectivo" class="metodo-btn activo" onclick="setMetodo('efectivo')">💵 Efectivo</button>
        <button type="button" id="btn-tarjeta" class="metodo-btn" onclick="setMetodo('tarjeta')">💳 Tarjeta</button>
        <button type="button" id="btn-credito" class="metodo-btn" onclick="setMetodo('credito')">📒 Crédito</button>
        <button type="button" id="btn-transferencia" class="metodo-btn" onclick="setMetodo('transferencia')">🏦 Transferencia</button>
      </div>'''
if viejo_grid in src:
    src = src.replace(viejo_grid, nuevo_grid, 1)
    cambios.append('botones de metodo de pago en cuadricula 2x2')
elif 'grid-template-columns:1fr 1fr;gap:8px">\n        <button type="button" id="btn-efectivo"' in src:
    cambios.append('* botones ya estaban en cuadricula')

# ================================================================
# 2a. Modal de descuento GENERAL: agregar toggle %/$
# ================================================================
viejo_html_general = '''    <h2>Descuento extra</h2>
    <div class="field"><label>Porcentaje de descuento (%)</label><input type="number" id="d-pct" min="0" max="100" step="1" placeholder="0"></div>'''
nuevo_html_general = '''    <h2>Descuento extra</h2>
    <div class="field">
      <label>Descuento</label>
      <div style="display:flex;gap:8px;margin-bottom:8px">
        <button type="button" id="desc-modo-pct" class="metodo-btn activo" onclick="setModoDescGeneral('pct')" style="flex:1">% Porcentaje</button>
        <button type="button" id="desc-modo-monto" class="metodo-btn" onclick="setModoDescGeneral('monto')" style="flex:1">$ Monto</button>
      </div>
      <input type="number" id="d-valor" min="0" step="0.01" placeholder="0">
    </div>'''
if viejo_html_general in src:
    src = src.replace(viejo_html_general, nuevo_html_general, 1)
    cambios.append('modal de descuento general: toggle %/$ agregado')
elif 'desc-modo-pct' in src:
    cambios.append('* modal de descuento general ya tenia el toggle')

viejo_js_general = '''function abrirDescuento(){
  if(!carrito.length)return;
  document.getElementById('d-pct').value=descuentoExtra||'';
  document.getElementById('desc-msg').className='msg';
  document.getElementById('desc-modal').classList.add('open');
}
function cerrarDescuento(){document.getElementById('desc-modal').classList.remove('open');}
function autorizarDescuento(){
  const pct = parseFloat(document.getElementById('d-pct').value);
  const msg = document.getElementById('desc-msg');
  if(isNaN(pct)||pct<0||pct>100){msg.className='msg error show';msg.textContent='Porcentaje inválido';return;}
  descuentoExtra=pct;
  autorizadoPor=sesionPOS?sesionPOS.usuario:null;
  actualizarTotales();
  cerrarDescuento();
}'''
nuevo_js_general = '''let modoDescGeneral = 'pct';
function setModoDescGeneral(modo){
  modoDescGeneral = modo;
  document.getElementById('desc-modo-pct').classList.toggle('activo', modo==='pct');
  document.getElementById('desc-modo-monto').classList.toggle('activo', modo==='monto');
  document.getElementById('d-valor').placeholder = modo==='pct' ? '0' : '0.00';
}
function abrirDescuento(){
  if(!carrito.length)return;
  setModoDescGeneral('pct');
  document.getElementById('d-valor').value=descuentoExtra||'';
  document.getElementById('desc-msg').className='msg';
  document.getElementById('desc-modal').classList.add('open');
}
function cerrarDescuento(){document.getElementById('desc-modal').classList.remove('open');}
function autorizarDescuento(){
  const valor = parseFloat(document.getElementById('d-valor').value);
  const msg = document.getElementById('desc-msg');
  if(isNaN(valor)||valor<0){msg.className='msg error show';msg.textContent='Valor inválido';return;}
  let pct;
  if(modoDescGeneral==='monto'){
    const subtotal = calcSubtotal();
    if(subtotal<=0){msg.className='msg error show';msg.textContent='El carrito está vacío';return;}
    if(valor>subtotal){msg.className='msg error show';msg.textContent='El monto no puede ser mayor al subtotal';return;}
    pct = Math.round((valor/subtotal)*10000)/100;
  }else{
    if(valor>100){msg.className='msg error show';msg.textContent='El porcentaje no puede ser mayor a 100';return;}
    pct = valor;
  }
  descuentoExtra=pct;
  autorizadoPor=sesionPOS?sesionPOS.usuario:null;
  actualizarTotales();
  cerrarDescuento();
}'''
if viejo_js_general in src:
    src = src.replace(viejo_js_general, nuevo_js_general, 1)
    cambios.append('logica de descuento general: soporta %/$ ')
elif 'modoDescGeneral' in src:
    cambios.append('* logica de descuento general ya soportaba %/$')
else:
    print("ERROR: no se encontro el bloque JS del descuento general")

# ================================================================
# 2b. Modal de descuento POR ARTICULO: agregar toggle %/$
# ================================================================
viejo_html_item = '''    <h2>Descuento por artículo</h2>
    <p id="item-desc-nombre" style="font-size:13px;color:var(--text2);margin-bottom:12px"></p>
    <div class="field"><label>Porcentaje de descuento (%)</label><input type="number" id="item-desc-pct" min="0" max="100" step="1" placeholder="0"></div>'''
nuevo_html_item = '''    <h2>Descuento por artículo</h2>
    <p id="item-desc-nombre" style="font-size:13px;color:var(--text2);margin-bottom:12px"></p>
    <div class="field">
      <label>Descuento</label>
      <div style="display:flex;gap:8px;margin-bottom:8px">
        <button type="button" id="item-desc-modo-pct" class="metodo-btn activo" onclick="setModoDescItem('pct')" style="flex:1">% Porcentaje</button>
        <button type="button" id="item-desc-modo-monto" class="metodo-btn" onclick="setModoDescItem('monto')" style="flex:1">$ Monto</button>
      </div>
      <input type="number" id="item-desc-valor" min="0" step="0.01" placeholder="0">
    </div>'''
if viejo_html_item in src:
    src = src.replace(viejo_html_item, nuevo_html_item, 1)
    cambios.append('modal de descuento por articulo: toggle %/$ agregado')
elif 'item-desc-modo-pct' in src:
    cambios.append('* modal de descuento por articulo ya tenia el toggle')

viejo_js_item = '''let itemDescuentoActualId = null;

function descuentoItem(id){
  const c = carrito.find(x=>x.id===id);
  if(!c) return;
  itemDescuentoActualId = id;
  const actual = (c.precioOriginal && c.precioOriginal>c.precio) ? Math.round((1-c.precio/c.precioOriginal)*100) : 0;
  document.getElementById('item-desc-nombre').textContent = c.nombre + ' — Precio original: ' + money(c.precioOriginal);
  document.getElementById('item-desc-pct').value = actual || '';
  document.getElementById('item-desc-msg').className = 'msg';
  document.getElementById('item-desc-modal').classList.add('open');
}

function cerrarDescuentoItem(){
  document.getElementById('item-desc-modal').classList.remove('open');
  itemDescuentoActualId = null;
}

function aplicarDescuentoItem(){
  const c = carrito.find(x=>x.id===itemDescuentoActualId);
  const msg = document.getElementById('item-desc-msg');
  if(!c){ cerrarDescuentoItem(); return; }
  const pct = parseFloat(document.getElementById('item-desc-pct').value);
  if(isNaN(pct) || pct<0 || pct>100){ msg.className='msg error show'; msg.textContent='Porcentaje inválido (0-100)'; return; }
  c.precio = Math.round(c.precioOriginal * (1 - pct/100) * 100) / 100;
  renderCarrito();
  cerrarDescuentoItem();
}'''
nuevo_js_item = '''let itemDescuentoActualId = null;
let modoDescItem = 'pct';
function setModoDescItem(modo){
  modoDescItem = modo;
  document.getElementById('item-desc-modo-pct').classList.toggle('activo', modo==='pct');
  document.getElementById('item-desc-modo-monto').classList.toggle('activo', modo==='monto');
  document.getElementById('item-desc-valor').placeholder = modo==='pct' ? '0' : '0.00';
}

function descuentoItem(id){
  const c = carrito.find(x=>x.id===id);
  if(!c) return;
  itemDescuentoActualId = id;
  setModoDescItem('pct');
  const actual = (c.precioOriginal && c.precioOriginal>c.precio) ? Math.round((1-c.precio/c.precioOriginal)*100) : 0;
  document.getElementById('item-desc-nombre').textContent = c.nombre + ' — Precio original: ' + money(c.precioOriginal);
  document.getElementById('item-desc-valor').value = actual || '';
  document.getElementById('item-desc-msg').className = 'msg';
  document.getElementById('item-desc-modal').classList.add('open');
}

function cerrarDescuentoItem(){
  document.getElementById('item-desc-modal').classList.remove('open');
  itemDescuentoActualId = null;
}

function aplicarDescuentoItem(){
  const c = carrito.find(x=>x.id===itemDescuentoActualId);
  const msg = document.getElementById('item-desc-msg');
  if(!c){ cerrarDescuentoItem(); return; }
  const valor = parseFloat(document.getElementById('item-desc-valor').value);
  if(isNaN(valor) || valor<0){ msg.className='msg error show'; msg.textContent='Valor inválido'; return; }
  let nuevoPrecio;
  if(modoDescItem==='monto'){
    if(valor>c.precioOriginal){ msg.className='msg error show'; msg.textContent='El monto no puede ser mayor al precio original'; return; }
    nuevoPrecio = Math.round((c.precioOriginal - valor) * 100) / 100;
  }else{
    if(valor>100){ msg.className='msg error show'; msg.textContent='Porcentaje inválido (0-100)'; return; }
    nuevoPrecio = Math.round(c.precioOriginal * (1 - valor/100) * 100) / 100;
  }
  c.precio = nuevoPrecio;
  renderCarrito();
  cerrarDescuentoItem();
}'''
if viejo_js_item in src:
    src = src.replace(viejo_js_item, nuevo_js_item, 1)
    cambios.append('logica de descuento por articulo: soporta %/$ ')
elif 'modoDescItem' in src:
    cambios.append('* logica de descuento por articulo ya soportaba %/$')
else:
    print("ERROR: no se encontro el bloque JS del descuento por articulo")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print()
    for c in cambios:
        print("OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Botones en cuadricula 2x2, y ambos descuentos ahora")
    print("permiten elegir entre % o $ para el monto.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
