#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend de "ventas en espera": botones + modal en pagos.html.
Corre DESPUES de ventas_pendientes_backend.py
Uso: cd ~/inventario/static && python3 ventas_pendientes_frontend.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Boton con badge en el topbar (junto al de Historial)
# ================================================================
viejo_topbar = '''  <a href="/historial" class="icon-btn" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none" title="Historial">📋</a>'''

nuevo_topbar = '''  <button class="icon-btn" onclick="abrirPendientes()" title="Ventas en espera" style="position:relative">
    ⏸<span id="badge-pendientes" style="display:none;position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;font-size:10px;font-weight:700;border-radius:10px;min-width:16px;height:16px;align-items:center;justify-content:center;padding:0 3px"></span>
  </button>
  <a href="/historial" class="icon-btn" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none" title="Historial">📋</a>'''

n = src.count(viejo_topbar)
if n == 1:
    src = src.replace(viejo_topbar, nuevo_topbar, 1)
    cambios.append('Boton de pendientes agregado al topbar')
else:
    print("ADVERTENCIA: no se encontro (o se encontro mas de una vez) el enlace de Historial. Coincidencias: " + str(n))

# ================================================================
# 2. Boton "Dejar en espera" antes de Cobrar
# ================================================================
viejo_cobrar = '<button class="btn-cobrar" id="btn-cobrar" onclick="abrirCobro()" disabled>Cobrar</button>'
nuevo_cobrar = '''<button onclick="dejarEnEspera()" style="width:100%;height:40px;margin-bottom:8px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-size:14px;cursor:pointer">⏸ Dejar en espera</button>
      <button class="btn-cobrar" id="btn-cobrar" onclick="abrirCobro()" disabled>Cobrar</button>'''

n = src.count(viejo_cobrar)
if n == 1:
    src = src.replace(viejo_cobrar, nuevo_cobrar, 1)
    cambios.append('Boton "Dejar en espera" agregado junto a Cobrar')
else:
    print("ADVERTENCIA: coincidencias inesperadas para el boton Cobrar: " + str(n))

# ================================================================
# 3. Modal de ventas en espera (antes del modal de ticket, o al final del body)
# ================================================================
modal_pendientes = '''
<!-- Modal ventas en espera -->
<div class="overlay" id="pendientes-modal">
  <div class="modal">
    <h2>⏸ Ventas en espera</h2>
    <div id="pendientes-lista" style="max-height:340px;overflow-y:auto"></div>
    <div class="modal-footer">
      <button onclick="cerrarPendientes()">Cerrar</button>
    </div>
  </div>
</div>
'''

if 'pendientes-modal' not in src:
    if '</body>' in src:
        src = src.replace('</body>', modal_pendientes + '\n</body>', 1)
        cambios.append('Modal de ventas en espera agregado')
    else:
        print("ADVERTENCIA: no se encontro </body> para insertar el modal")

# ================================================================
# 4. Funciones JS (antes de renderCarrito)
# ================================================================
funciones_js = '''function toastSeguro(msg){
  if(typeof toast==='function'){ toast(msg); }
}

async function actualizarBadgePendientes(){
  try{
    const r = await authFetch('/api/pos/pendientes');
    const lista = await r.json();
    const badge = document.getElementById('badge-pendientes');
    if(lista.length>0){
      badge.textContent = lista.length;
      badge.style.display='flex';
    }else{
      badge.style.display='none';
    }
  }catch(e){}
}

async function abrirPendientes(){
  const cont = document.getElementById('pendientes-lista');
  cont.innerHTML = 'Cargando...';
  document.getElementById('pendientes-modal').classList.add('open');
  try{
    const r = await authFetch('/api/pos/pendientes');
    const lista = await r.json();
    if(!lista.length){
      cont.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text2)">No hay ventas en espera</div>';
      return;
    }
    cont.innerHTML = lista.map(p=>{
      const fecha = new Date(p.creado_en).toLocaleString('es-MX',{hour:'2-digit',minute:'2-digit',day:'numeric',month:'short'});
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:.75rem 0;border-bottom:0.5px solid var(--border)">
        <div>
          <div style="font-weight:600;font-size:14px">${p.nota?esc(p.nota):('Venta de '+esc(p.operador||''))}</div>
          <div style="font-size:12px;color:var(--text2)">${p.num_items} artículo(s) · ${money(p.total_aprox)} · ${fecha}</div>
        </div>
        <div style="display:flex;gap:6px">
          <button onclick="reanudarPendiente(${p.id})" style="height:34px;padding:0 12px;border:none;border-radius:8px;background:var(--blue);color:#fff;font-size:13px;cursor:pointer">Reanudar</button>
          <button onclick="borrarPendiente(${p.id})" style="height:34px;padding:0 10px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--red);font-size:13px;cursor:pointer">🗑</button>
        </div>
      </div>`;
    }).join('');
  }catch(e){
    cont.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text2)">Error al cargar</div>';
  }
}

function cerrarPendientes(){
  document.getElementById('pendientes-modal').classList.remove('open');
}

async function dejarEnEspera(){
  if(!carrito.length){ alert('El carrito está vacío'); return; }
  const nota = prompt('Nota para identificar esta venta (opcional):', '');
  if(nota===null) return;
  try{
    const r = await authFetch('/api/pos/pendientes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({carrito, descuento_extra_pct: descuentoExtra, autorizado_por: autorizadoPor, nota: nota||null})
    });
    if(!r.ok){ alert('No se pudo dejar en espera'); return; }
    carrito = [];
    descuentoExtra = 0;
    autorizadoPor = null;
    renderCarrito();
    toastSeguro('Venta dejada en espera');
  }catch(e){ alert('Error de conexión'); }
}

async function reanudarPendiente(id){
  if(carrito.length>0){
    const confirmar = confirm('Ya tienes productos en el carrito actual. Si continúas, se perderán. ¿Continuar de todas formas?');
    if(!confirmar) return;
  }
  try{
    const r = await authFetch('/api/pos/pendientes/'+id);
    if(!r.ok){ alert('No se pudo cargar la venta en espera'); return; }
    const data = await r.json();
    carrito = data.carrito || [];
    descuentoExtra = data.descuento_extra_pct || 0;
    autorizadoPor = data.autorizado_por || null;
    await authFetch('/api/pos/pendientes/'+id, {method:'DELETE'});
    renderCarrito();
    cerrarPendientes();
  }catch(e){ alert('Error de conexión'); }
}

async function borrarPendiente(id){
  if(!confirm('¿Eliminar esta venta en espera? No se puede deshacer.')) return;
  try{
    await authFetch('/api/pos/pendientes/'+id, {method:'DELETE'});
    abrirPendientes();
    actualizarBadgePendientes();
  }catch(e){}
}

'''

if 'function abrirPendientes' not in src:
    marcador = 'function renderCarrito(){'
    if marcador in src:
        src = src.replace(marcador, funciones_js + marcador, 1)
        cambios.append('Funciones JS de ventas en espera agregadas')
    else:
        print("ERROR: no se encontro 'function renderCarrito(){' para insertar las funciones")

# ================================================================
# 5. Enganchar actualizarBadgePendientes() dentro de renderCarrito
#    para que el contador se refresque solo, y llamarlo al cargar
# ================================================================
viejo_a = '''    descuentoExtra=0;autorizadoPor=null;
    actualizarTotales();
    document.getElementById('btn-cobrar').disabled=true;
    return;'''
nuevo_a = '''    descuentoExtra=0;autorizadoPor=null;
    actualizarTotales();
    actualizarBadgePendientes();
    document.getElementById('btn-cobrar').disabled=true;
    return;'''
if src.count(viejo_a) == 1:
    src = src.replace(viejo_a, nuevo_a, 1)
    cambios.append('actualizarBadgePendientes() enganchado (carrito vacio)')

viejo_b = '''  actualizarTotales();
  document.getElementById('btn-cobrar').disabled=false;
}'''
nuevo_b = '''  actualizarTotales();
  actualizarBadgePendientes();
  document.getElementById('btn-cobrar').disabled=false;
}'''
if src.count(viejo_b) == 1:
    src = src.replace(viejo_b, nuevo_b, 1)
    cambios.append('actualizarBadgePendientes() enganchado (carrito con items)')

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print()
    print("Cambios aplicados:")
    for c in cambios:
        print("  OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Ya puedes dejar ventas en espera y reanudarlas desde el boton ⏸ del topbar.")
else:
    print("ADVERTENCIA: desbalance de llaves detectado. NO se reinicio el servicio.")
    print("Revisa static/pagos.html manualmente antes de reiniciar.")
