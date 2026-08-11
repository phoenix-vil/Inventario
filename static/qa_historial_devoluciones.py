#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. En el historial, distinguir devoluciones de ventas: titulo
    "Devolucion #N" con referencia al ticket original, y el monto en rojo.
 2. Renombrar el tile del menu: "Historial de ventas" -> "Historial".
Uso: cd ~/inventario-qa/static && python3 qa_historial_devoluciones.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

# ============================================================
# 1. historial.html: distinguir devoluciones
# ============================================================
ruta = os.path.join(STATIC, 'historial.html')
src = open(ruta, encoding='utf-8').read()

viejo = '''    const etiquetasMet={tarjeta:'💳 Tarjeta',credito:'📒 Crédito',transferencia:'🏦 Transferencia',efectivo:'💵 Efectivo'};
    const met=etiquetasMet[v.metodo_pago]||'💵 Efectivo';
    return `<div class="venta" onclick="verDetalle(${v.id})">
      <div>
        <div class="v-id">Venta #${v.id}</div>
        <div class="v-fecha">${fecha} · ${met}</div>
        <div class="v-items">${v.num_items} artículo${v.num_items!==1?'s':''}</div>
        ${op}
      </div>'''
nuevo = '''    const etiquetasMet={tarjeta:'💳 Tarjeta',credito:'📒 Crédito',transferencia:'🏦 Transferencia',efectivo:'💵 Efectivo'};
    const met=etiquetasMet[v.metodo_pago]||'💵 Efectivo';
    const esDev = (v.estado==='devolucion') || (v.total<0);
    const titulo = esDev
      ? `<div class="v-id" style="color:var(--red)">↩️ Devolución #${v.id}</div>`
        + (v.venta_origen_id?`<div class="v-items">del ticket #${v.venta_origen_id}</div>`:'')
      : `<div class="v-id">Venta #${v.id}</div>`;
    const badgeEstado = (!esDev && (v.estado==='parcial'||v.estado==='devuelta'))
      ? `<div class="v-items" style="color:var(--amber)">${v.estado==='devuelta'?'Devuelta por completo':'Con devolución parcial'}</div>`
      : '';
    return `<div class="venta" onclick="verDetalle(${v.id})">
      <div>
        ${titulo}
        <div class="v-fecha">${fecha} · ${met}</div>
        <div class="v-items">${v.num_items} artículo${v.num_items!==1?'s':''}</div>
        ${badgeEstado}
        ${op}
      </div>'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK historial: las devoluciones se distinguen de las ventas")
elif 'Devolución #${v.id}' in src:
    res.append("* historial: ya se distinguian")
else:
    res.append("ERROR historial: no se encontro el bloque de render()")

# --- mensaje de lista vacia ---
src = src.replace("No hay ventas en este periodo", "No hay movimientos en este periodo")

# --- monto en rojo si es negativo ---
m = re.search(r'(<div style="text-align:right">\s*\n\s*)(<div class="v-total">)', src)
if m and 'v-total" style="color' not in src:
    src = src[:m.start(2)] + '<div class="v-total" style="' + '${v.total<0?\'color:var(--red)\':\'\'}' + '">' + src[m.end(2):]
    res.append("OK historial: los montos negativos se muestran en rojo")

open(ruta, 'w', encoding='utf-8').write(src)

# ============================================================
# 2. menu.html: renombrar el tile
# ============================================================
ruta = os.path.join(STATIC, 'menu.html')
src = open(ruta, encoding='utf-8').read()

viejo_m = '''      <div class="menu-title">Historial de ventas</div>
      <div class="menu-desc">Consulta y descarga tus ventas</div>'''
nuevo_m = '''      <div class="menu-title">Historial</div>
      <div class="menu-desc">Ventas, devoluciones y reportes</div>'''
if viejo_m in src:
    src = src.replace(viejo_m, nuevo_m, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK menu: tile renombrado a 'Historial'")
elif '<div class="menu-title">Historial</div>' in src:
    res.append("* menu: el tile ya estaba renombrado")
else:
    res.append("ADVERTENCIA menu: no se encontro el tile")

# ============================================================
print()
for r in res:
    print(r)

ok_total = True
print()
for nombre in ['historial.html', 'menu.html']:
    s = open(os.path.join(STATIC, nombre), encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 58)
if ok_total and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Ctrl+Shift+R y revisa el historial.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
