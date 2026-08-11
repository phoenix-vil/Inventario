#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega el articulo personalizado a Punto de Venta:
 1. Boton "+ Personalizado" junto al de descuento
 2. Modal para capturar descripcion/cantidad/precio
 3. El carrito muestra una etiqueta "Personalizado"
 4. confirmarCobro() manda producto_id:null + nombre para esos articulos
 5. importarCotizacion() YA NO omite los personalizados de la cotizacion,
    los agrega directo (sin necesidad de buscarlos en el inventario)
Uso: cd ~/inventario-qa/static && python3 qa_personalizado_pos.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
res = []

# ============================================================
# 1. Boton "+ Personalizado" junto al de descuento
# ============================================================
viejo1 = '      <button class="btn-desc" onclick="abrirDescuento()">% Descuento</button>'
nuevo1 = '''      <div style="display:flex;gap:8px;margin-bottom:8px">
        <button class="btn-desc" onclick="abrirDescuento()" style="width:auto;flex:1;margin-bottom:0">% Descuento</button>
        <button onclick="abrirCustomVenta()" style="flex:1;height:44px;border:0.5px dashed var(--border);border-radius:10px;background:transparent;color:var(--text2);font-size:13px;font-weight:600;cursor:pointer">+ Personalizado</button>
      </div>'''
if viejo1 in src:
    src = src.replace(viejo1, nuevo1, 1)
    res.append("OK: boton + Personalizado agregado junto al de descuento")
elif 'abrirCustomVenta()' in src:
    res.append("* el boton ya existia")
else:
    res.append("ERROR: no se encontro el boton de descuento (paso 1)")

# ============================================================
# 2. Modal HTML (se inserta antes del </body> real)
# ============================================================
if 'id="custom-venta-modal"' not in src:
    modal_html = '''
<!-- Modal articulo personalizado (Punto de Venta) -->
<div class="overlay" id="custom-venta-modal">
  <div class="modal">
    <h2>Artículo personalizado</h2>
    <div class="field"><label>Descripción *</label><input id="cv-desc" placeholder="Ej: Mano de obra, Instalación, Flete..." autocomplete="off"></div>
    <div class="field"><label>Cantidad</label><input type="number" id="cv-cant" value="1" min="0.01" step="any"></div>
    <div class="field"><label>Precio unitario *</label><input type="number" id="cv-precio" placeholder="0.00" min="0" step="0.01"></div>
    <div class="msg" id="custom-venta-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarCustomVenta()">Cancelar</button>
      <button class="primary" onclick="agregarCustomVenta()">Agregar</button>
    </div>
  </div>
</div>
'''
    patron_final = re.compile(r'</body>\s*</html>\s*$')
    nueva_src, n = patron_final.subn(modal_html + '\n</body>\n</html>\n', src, count=1)
    if n == 1:
        src = nueva_src
        res.append("OK: modal HTML insertado correctamente al final real del archivo")
    else:
        res.append("ERROR: no se encontro el patron final </body></html> (paso 2)")
else:
    res.append("* el modal ya existia")

# ============================================================
# 3. Funciones JS: abrir/cerrar/agregar personalizado
# ============================================================
if 'function abrirCustomVenta' not in src:
    ancla_js = 'function calcSubtotal(){return carrito.reduce((s,c)=>s+c.precio*c.cantidad,0);}'
    funciones = '''let _customVentaIdCounter = -1;
function abrirCustomVenta(){
  document.getElementById('cv-desc').value = '';
  document.getElementById('cv-cant').value = '1';
  document.getElementById('cv-precio').value = '';
  document.getElementById('custom-venta-msg').className = 'msg';
  document.getElementById('custom-venta-modal').classList.add('open');
  setTimeout(()=>document.getElementById('cv-desc').focus(), 60);
}
function cerrarCustomVenta(){ document.getElementById('custom-venta-modal').classList.remove('open'); }
function agregarCustomVenta(){
  const desc = document.getElementById('cv-desc').value.trim();
  const cant = parseFloat(document.getElementById('cv-cant').value);
  const precio = parseFloat(document.getElementById('cv-precio').value);
  const msg = document.getElementById('custom-venta-msg');
  if(!desc){ msg.className='msg error show'; msg.textContent='Escribe una descripción'; return; }
  if(isNaN(cant)||cant<=0){ msg.className='msg error show'; msg.textContent='Cantidad inválida'; return; }
  if(isNaN(precio)||precio<0){ msg.className='msg error show'; msg.textContent='Precio inválido'; return; }
  carrito.push({id:_customVentaIdCounter--, nombre:desc, precio:precio, precioOriginal:precio, cantidad:cant, vendido_por_peso:false, unidad:'', stock:999999, personalizado:true});
  cerrarCustomVenta();
  renderCarrito();
}

'''
    if ancla_js in src:
        src = src.replace(ancla_js, funciones + ancla_js, 1)
        res.append("OK: funciones abrirCustomVenta/agregarCustomVenta agregadas")
    else:
        res.append("ERROR: no se encontro calcSubtotal (paso 3)")
else:
    res.append("* las funciones ya existian")

# ============================================================
# 4. renderCarrito: etiqueta "Personalizado"
# ============================================================
viejo4 = '''    return `<div class="cart-item">
      <div class="ci-info">
        <div class="ci-name">${esc(c.nombre)}</div>
        <div class="ci-price-row">${precioLinea}</div>
      </div>'''
nuevo4 = '''    return `<div class="cart-item">
      <div class="ci-info">
        <div class="ci-name">${esc(c.nombre)}${c.personalizado?' <span class="ci-desc-badge" style="background:var(--blue-bg);color:var(--blue)">Personalizado</span>':''}</div>
        <div class="ci-price-row">${precioLinea}</div>
      </div>'''
if viejo4 in src:
    src = src.replace(viejo4, nuevo4, 1)
    res.append("OK: etiqueta 'Personalizado' agregada al carrito")
elif "Personalizado</span>':''" in src:
    res.append("* la etiqueta ya existia")
else:
    res.append("ERROR: no se encontro el bloque del carrito (paso 4)")

# ============================================================
# 5. confirmarCobro: mandar producto_id null + nombre
# ============================================================
viejo5 = "  const items=carrito.map(c=>({producto_id:c.id,cantidad:c.cantidad,precio_unitario:c.precio,precio_original:c.precioOriginal||null}));"
nuevo5 = '''  const items=carrito.map(c=>({
    producto_id: c.personalizado ? null : c.id,
    nombre: c.personalizado ? c.nombre : null,
    cantidad: c.cantidad,
    precio_unitario: c.precio,
    precio_original: c.personalizado ? null : (c.precioOriginal||null),
  }));'''
if viejo5 in src:
    src = src.replace(viejo5, nuevo5, 1)
    res.append("OK: confirmarCobro manda personalizados correctamente")
elif "producto_id: c.personalizado ? null : c.id," in src:
    res.append("* confirmarCobro ya estaba actualizado")
else:
    res.append("ERROR: no se encontro la construccion de items en confirmarCobro (paso 5)")

# ============================================================
# 6. importarCotizacion: ya no omite personalizados
# ============================================================
inicio = src.find('async function importarCotizacion(cotId){')
if inicio == -1:
    res.append("ERROR: no se encontro importarCotizacion (paso 6)")
else:
    prof = 0; enc = False; fin = -1
    for i in range(inicio, len(src)):
        c = src[i]
        if c == '{': prof += 1; enc = True
        elif c == '}':
            prof -= 1
            if enc and prof == 0:
                fin = i + 1
                break
    if fin == -1:
        res.append("ERROR: no se pudo delimitar importarCotizacion (paso 6)")
    else:
        nueva_funcion = '''async function importarCotizacion(cotId){
  try{
    const r = await authFetch('/api/cotizaciones/'+cotId);
    if(!r.ok){ alert('No se pudo cargar la cotización #'+cotId); return; }
    const cot = await r.json();
    const detalle = cot.detalle || [];

    let agregados = 0;
    const noEncontrados = [];
    for(const it of detalle){
      if(it.producto_id != null){
        try{
          const rp = await authFetch('/api/pos/producto/'+it.producto_id);
          if(!rp.ok){ noEncontrados.push(it.nombre); continue; }
          const p = await rp.json();
          const existente = carrito.find(c=>c.id===p.id && !c.personalizado);
          if(existente){
            existente.cantidad += it.cantidad;
          }else{
            carrito.push({
              id:p.id, nombre:p.nombre, precio:it.precio_unitario, precioOriginal:p.precio_venta,
              cantidad:it.cantidad, vendido_por_peso:p.vendido_por_peso, unidad:p.unidad, stock:p.stock,
              personalizado:false
            });
          }
          agregados++;
        }catch(e){ noEncontrados.push(it.nombre); }
      }else{
        carrito.push({
          id:_customVentaIdCounter--, nombre:it.nombre, precio:it.precio_unitario, precioOriginal:it.precio_unitario,
          cantidad:it.cantidad, vendido_por_peso:false, unidad:'', stock:999999, personalizado:true
        });
        agregados++;
      }
    }
    renderCarrito();

    let msg = 'Cotización #'+cotId+': se importaron '+agregados+' artículo(s).';
    if(noEncontrados.length){
      msg += ' No se encontraron en inventario: ' + noEncontrados.join(', ') + '.';
    }
    alert(msg);
  }catch(e){
    alert('Error al importar la cotización');
  }
}'''
        src = src[:inicio] + nueva_funcion + src[fin:]
        res.append("OK: importarCotizacion ahora incluye los articulos personalizados")

if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Este cambio es solo HTML/JS de pagos.html, no requiere reiniciar")
    print("el servicio. Prueba con Ctrl+Shift+R.")
else:
    print("Revisa los mensajes de arriba antes de probar.")
