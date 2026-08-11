#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Reemplaza el prompt() nativo del descuento por articulo con un
modal propio, mismo estilo que "Descuento extra" (el del carrito completo).
Uso: cd ~/inventario-qa/static && python3 qa_modal_descuento_item.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Agregar el modal HTML (antes del modal de cobro)
# ================================================================
if 'id="item-desc-modal"' not in src:
    modal_html = '''<!-- Modal descuento por articulo -->
<div class="overlay" id="item-desc-modal">
  <div class="modal">
    <h2>Descuento por artículo</h2>
    <p id="item-desc-nombre" style="font-size:13px;color:var(--text2);margin-bottom:12px"></p>
    <div class="field"><label>Porcentaje de descuento (%)</label><input type="number" id="item-desc-pct" min="0" max="100" step="1" placeholder="0"></div>
    <div class="msg" id="item-desc-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarDescuentoItem()">Cancelar</button>
      <button class="primary" onclick="aplicarDescuentoItem()">Aplicar</button>
    </div>
  </div>
</div>
<!-- Modal cobro -->'''

    marcador = '<!-- Modal cobro -->'
    if marcador in src:
        src = src.replace(marcador, modal_html, 1)
        cambios.append('modal HTML agregado')
    else:
        print("ERROR: no se encontro '<!-- Modal cobro -->'")
else:
    cambios.append('* modal HTML ya existia')

# ================================================================
# 2. Reemplazar descuentoItem() y agregar las funciones del modal
# ================================================================
viejo_funcion = '''function descuentoItem(id){
  const c = carrito.find(x=>x.id===id);
  if(!c) return;
  const actual = (c.precioOriginal && c.precioOriginal>c.precio) ? Math.round((1-c.precio/c.precioOriginal)*100) : 0;
  const pctStr = prompt(`Descuento (%) para "${c.nombre}"\\nPrecio original: ${money(c.precioOriginal)}`, actual || '');
  if(pctStr===null) return;
  const pct = parseFloat(pctStr);
  if(isNaN(pct) || pct<0 || pct>100){ alert('Porcentaje inválido (0-100)'); return; }
  c.precio = Math.round(c.precioOriginal * (1 - pct/100) * 100) / 100;
  renderCarrito();
}'''

nueva_funcion = '''let itemDescuentoActualId = null;

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

if viejo_funcion in src:
    src = src.replace(viejo_funcion, nueva_funcion, 1)
    cambios.append('descuentoItem() reemplazada por version con modal')
elif 'function aplicarDescuentoItem' in src:
    cambios.append('* funciones del modal ya existian')
else:
    print("ERROR: no se encontro la funcion descuentoItem exacta")

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
    print("Listo. El boton de % ahora abre un modal propio, con el mismo")
    print("estilo que el modal de Descuento extra.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
