#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Agrega el porcentaje de vuelta a la linea de "Descuento" por item.
2. Oculta el nombre del autorizador en la linea de descuento general.
Uso: cd ~/inventario-qa/static && python3 qa_ajuste_descuentos_final.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo_item = '''    if(tieneDescItem){
      html+=`<div class="tk-line tk-desc"><span>Descuento</span><span>-${money(it.ahorro)}</span></div>`;
    }'''
nuevo_item = '''    if(tieneDescItem){
      html+=`<div class="tk-line tk-desc"><span>Descuento ${Math.round((1-it.precio_unitario/it.precio_original)*100)}%</span><span>-${money(it.ahorro)}</span></div>`;
    }'''

viejo_general = '''    html+=`<div class="tk-line tk-desc"><span>Descuento ${v.descuento_extra_pct}%${v.autorizado_por?' ('+esc(v.autorizado_por)+')':''}</span><span>-${money(v.subtotal*v.descuento_extra_pct/100)}</span></div>`;'''
nuevo_general = '''    html+=`<div class="tk-line tk-desc"><span>Descuento ${v.descuento_extra_pct}%</span><span>-${money(v.subtotal*v.descuento_extra_pct/100)}</span></div>`;'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    cambios = []

    if viejo_item in src:
        src = src.replace(viejo_item, nuevo_item, 1)
        cambios.append('porcentaje agregado al descuento por item')
    elif 'Descuento ${Math.round' in src:
        cambios.append('* descuento por item ya tenia el porcentaje')

    if viejo_general in src:
        src = src.replace(viejo_general, nuevo_general, 1)
        cambios.append('autorizador ocultado del descuento general')
    elif 'Descuento ${v.descuento_extra_pct}%</span>' in src:
        cambios.append('* autorizador ya estaba oculto')

    if cambios:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios:
            print("OK " + nombre + ": " + c)
        total += 1
    else:
        print("ERROR " + nombre + ": no se encontro ningun patron esperado")

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
    print("Listo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
