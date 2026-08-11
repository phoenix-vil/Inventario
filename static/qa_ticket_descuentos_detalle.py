#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Muestra el porcentaje de descuento aplicado junto a cada producto
que lo tenga (usando precio_original vs precio_unitario del detalle).
Como esto vive en generarTicketHTML/ticketHTML, se refleja automaticamente
en Descargar, Imprimir y WhatsApp (los tres comparten el mismo HTML).
Uso: cd ~/inventario-qa/static && python3 qa_ticket_descuentos_detalle.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo = '''  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(it.importe)}</span></div>`;
  });'''

nuevo = '''  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    const tieneDescItem = it.precio_original!=null && it.precio_original>it.precio_unitario;
    const badgeDesc = tieneDescItem
      ? ` <span style="color:#a32d2d;font-weight:600">(-${Math.round((1-it.precio_unitario/it.precio_original)*100)}%)</span>`
      : '';
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}${badgeDesc}</span><span>${money(it.importe)}</span></div>`;
  });'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": porcentaje de descuento por producto agregado")
        total += 1
    elif 'tieneDescItem' in src:
        print("* " + nombre + ": ya estaba agregado")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

print()
ok_total = True
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 55)
if ok_total:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Los productos con descuento ahora muestran el % aplicado")
    print("junto a su nombre, en las tres vistas (Descargar/Imprimir/WhatsApp).")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
