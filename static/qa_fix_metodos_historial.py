#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige los 4 lugares de historial.html donde solo se contemplaba
tarjeta vs efectivo, dejando credito y transferencia mal etiquetados:
 1. Etiqueta en la lista de ventas
 2. Ticket HTML (ticketHTML)
 3. Texto para compartir
 4. Exportacion CSV
Uso: cd ~/inventario-qa/static && python3 qa_fix_metodos_historial.py
"""
import os, re

HIST = os.path.expanduser('~/inventario-qa/static/historial.html')
src = open(HIST, encoding='utf-8').read()
original = src
cambios = []

# ── 1. Etiqueta en la lista ──────────────────────────────────────
viejo1 = "    const met=v.metodo_pago==='tarjeta'?'💳 Tarjeta':'💵 Efectivo';"
nuevo1 = """    const etiquetasMet={tarjeta:'💳 Tarjeta',credito:'📒 Crédito',transferencia:'🏦 Transferencia',efectivo:'💵 Efectivo'};
    const met=etiquetasMet[v.metodo_pago]||'💵 Efectivo';"""
if viejo1 in src:
    src = src.replace(viejo1, nuevo1, 1)
    cambios.append('etiqueta de la lista corregida')
elif 'etiquetasMet' in src:
    cambios.append('* etiqueta de la lista ya estaba corregida')
else:
    print("ERROR: no se encontro la linea de la etiqueta")

# ── 2. Ticket HTML ───────────────────────────────────────────────
viejo2 = '''  if(v.metodo_pago==='tarjeta'){
    html+=`<div class="tk-line"><span>Pago</span><span>TARJETA</span></div>`;
    if(v.tpv_terminal)html+=`<div class="tk-line"><span>Terminal</span><span>${esc(v.tpv_terminal)}</span></div>`;
    if(v.tpv_referencia)html+=`<div class="tk-line"><span>Referencia</span><span>${esc(v.tpv_referencia)}</span></div>`;
    if(v.tpv_autorizacion)html+=`<div class="tk-line"><span>Autorización</span><span>${esc(v.tpv_autorizacion)}</span></div>`;
  }else{'''
nuevo2 = '''  if(v.metodo_pago==='tarjeta'){
    html+=`<div class="tk-line"><span>Pago</span><span>TARJETA</span></div>`;
    if(v.tpv_terminal)html+=`<div class="tk-line"><span>Terminal</span><span>${esc(v.tpv_terminal)}</span></div>`;
    if(v.tpv_referencia)html+=`<div class="tk-line"><span>Referencia</span><span>${esc(v.tpv_referencia)}</span></div>`;
    if(v.tpv_autorizacion)html+=`<div class="tk-line"><span>Autorización</span><span>${esc(v.tpv_autorizacion)}</span></div>`;
  }else if(v.metodo_pago==='credito'){
    html+=`<div class="tk-line" style="color:var(--amber)"><span>Pago</span><span>A CRÉDITO</span></div>`;
    if(v.cliente_nombre)html+=`<div class="tk-line"><span>Cliente</span><span>${esc(v.cliente_nombre)}</span></div>`;
  }else if(v.metodo_pago==='transferencia'){
    html+=`<div class="tk-line"><span>Pago</span><span>TRANSFERENCIA</span></div>`;
    if(v.transferencia_referencia)html+=`<div class="tk-line"><span>Referencia</span><span>${esc(v.transferencia_referencia)}</span></div>`;
  }else{'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    cambios.append('ticket HTML corregido')
elif "TRANSFERENCIA</span></div>" in src:
    cambios.append('* ticket HTML ya estaba corregido')
else:
    print("ERROR: no se encontro el bloque del ticket HTML")

# ── 3. Texto para compartir ──────────────────────────────────────
viejo3 = '''  if(v.metodo_pago==='tarjeta'){
    txt+=`💳 Pago: Tarjeta`;
    if(v.tpv_terminal)txt+=` (${v.tpv_terminal})`;
    txt+=`\\n`;
    if(v.tpv_referencia)txt+=`Ref: ${v.tpv_referencia}\\n`;
  }else if(v.pago_con){'''
nuevo3 = '''  if(v.metodo_pago==='tarjeta'){
    txt+=`💳 Pago: Tarjeta`;
    if(v.tpv_terminal)txt+=` (${v.tpv_terminal})`;
    txt+=`\\n`;
    if(v.tpv_referencia)txt+=`Ref: ${v.tpv_referencia}\\n`;
  }else if(v.metodo_pago==='credito'){
    txt+=`📒 Pago: A crédito`;
    if(v.cliente_nombre)txt+=` (${v.cliente_nombre})`;
    txt+=`\\n`;
  }else if(v.metodo_pago==='transferencia'){
    txt+=`🏦 Pago: Transferencia\\n`;
    if(v.transferencia_referencia)txt+=`Ref: ${v.transferencia_referencia}\\n`;
  }else if(v.pago_con){'''
if viejo3 in src:
    src = src.replace(viejo3, nuevo3, 1)
    cambios.append('texto para compartir corregido')
elif 'Pago: Transferencia' in src:
    cambios.append('* texto para compartir ya estaba corregido')
else:
    print("ERROR: no se encontro el bloque del texto para compartir")

# ── 4. Exportacion CSV ───────────────────────────────────────────
viejo4 = "    const metodo=v.metodo_pago==='tarjeta'?'Tarjeta':'Efectivo';"
nuevo4 = """    const nombresMet={tarjeta:'Tarjeta',credito:'Crédito',transferencia:'Transferencia',efectivo:'Efectivo'};
    const metodo=nombresMet[v.metodo_pago]||'Efectivo';"""
if viejo4 in src:
    src = src.replace(viejo4, nuevo4, 1)
    cambios.append('exportacion CSV corregida')
elif 'nombresMet' in src:
    cambios.append('* exportacion CSV ya estaba corregida')
else:
    print("ERROR: no se encontro la linea del CSV")

if src != original:
    open(HIST, 'w', encoding='utf-8').write(src)
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
    print("Listo. La lista, el ticket, el texto compartido y el CSV")
    print("ahora muestran los 4 metodos correctamente.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
