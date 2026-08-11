#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend: envia la medianoche local de hoy al backend (para el chequeo
de vigencia) y muestra el mensaje si ya se alcanzo el limite de 2.
Corre DESPUES de limites_ventas_espera.py
Uso: cd ~/inventario/static && python3 limites_ventas_espera_frontend.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Helper hoyInicioISO() - medianoche local de hoy, como ISO
# ================================================================
if 'function hoyInicioISO' not in src:
    helper = '''function hoyInicioISO(){
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0).toISOString();
}

'''
    marcador = 'async function abrirPendientes(){'
    if marcador in src:
        src = src.replace(marcador, helper + marcador, 1)
        cambios.append('funcion hoyInicioISO() agregada')
    else:
        print("ERROR: no se encontro 'async function abrirPendientes(){'")

# ================================================================
# 2. abrirPendientes(): mandar hoy_inicio en la consulta
# ================================================================
viejo_abrir = '''    const r = await authFetch('/api/pos/pendientes');
    const lista = await r.json();
    if(!lista.length){
      cont.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text2)">No hay ventas en espera</div>';
      return;
    }'''

nuevo_abrir = '''    const r = await authFetch('/api/pos/pendientes?hoy_inicio='+encodeURIComponent(hoyInicioISO()));
    const lista = await r.json();
    if(!lista.length){
      cont.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text2)">No hay ventas en espera</div>';
      return;
    }'''

n1 = src.count(viejo_abrir)
if n1 == 1:
    src = src.replace(viejo_abrir, nuevo_abrir, 1)
    cambios.append('abrirPendientes() envia hoy_inicio')
elif "pendientes?hoy_inicio=" in src:
    print("* abrirPendientes ya enviaba hoy_inicio")
else:
    print("ERROR: no se encontro el bloque exacto de abrirPendientes")

# ================================================================
# 3. actualizarBadgePendientes(): mandar hoy_inicio tambien
# ================================================================
viejo_badge = '''  try{
    const r = await authFetch('/api/pos/pendientes');
    const lista = await r.json();
    const badge = document.getElementById('badge-pendientes');'''

nuevo_badge = '''  try{
    const r = await authFetch('/api/pos/pendientes?hoy_inicio='+encodeURIComponent(hoyInicioISO()));
    const lista = await r.json();
    const badge = document.getElementById('badge-pendientes');'''

n2 = src.count(viejo_badge)
if n2 == 1:
    src = src.replace(viejo_badge, nuevo_badge, 1)
    cambios.append('actualizarBadgePendientes() envia hoy_inicio')
elif "pendientes?hoy_inicio=" in src and src.count("pendientes?hoy_inicio=") >= 2:
    print("* actualizarBadgePendientes ya enviaba hoy_inicio")
else:
    print("ERROR: no se encontro el bloque exacto de actualizarBadgePendientes")

# ================================================================
# 4. dejarEnEspera(): mandar hoy_inicio y mostrar el mensaje real
#    del backend si ya se alcanzo el limite de 2
# ================================================================
viejo_dejar = '''async function dejarEnEspera(){
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
}'''

nuevo_dejar = '''async function dejarEnEspera(){
  if(!carrito.length){ alert('El carrito está vacío'); return; }
  const nota = prompt('Nota para identificar esta venta (opcional):', '');
  if(nota===null) return;
  try{
    const r = await authFetch('/api/pos/pendientes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({carrito, descuento_extra_pct: descuentoExtra, autorizado_por: autorizadoPor, nota: nota||null, hoy_inicio: hoyInicioISO()})
    });
    if(!r.ok){
      const data = await r.json().catch(()=>({}));
      alert(data.detail||'No se pudo dejar en espera');
      return;
    }
    carrito = [];
    descuentoExtra = 0;
    autorizadoPor = null;
    renderCarrito();
    toastSeguro('Venta dejada en espera');
  }catch(e){ alert('Error de conexión'); }
}'''

n3 = src.count(viejo_dejar)
if n3 == 1:
    src = src.replace(viejo_dejar, nuevo_dejar, 1)
    cambios.append('dejarEnEspera() envia hoy_inicio y muestra el error real del limite')
elif 'hoy_inicio: hoyInicioISO()' in src:
    print("* dejarEnEspera ya estaba actualizado")
else:
    print("ERROR: no se encontro el bloque exacto de dejarEnEspera")

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
    print("Listo. Maximo 2 ventas en espera por sucursal, y expiran a medianoche.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
