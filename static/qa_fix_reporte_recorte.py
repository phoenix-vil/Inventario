#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el recorte del reporte PDF: el contenedor de 700px se
capturaba pero al meterlo en una hoja de 595pt se cortaban los montos
de la derecha. Se ajusta el ancho del contenedor y se agrega box-sizing
para que el padding no expanda el ancho total.
Aplica a historial.html y dashboard.html.
Uso: cd ~/inventario-qa/static && python3 qa_fix_reporte_recorte.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo = """  cont.style.width='700px'; cont.style.background='#ffffff'; cont.style.padding='28px 32px';"""
nuevo = """  cont.style.width='595px'; cont.style.boxSizing='border-box'; cont.style.background='#ffffff'; cont.style.padding='28px 32px';"""

total = 0
for nombre in ['historial.html', 'dashboard.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n >= 1:
        src = src.replace(viejo, nuevo)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": ancho del reporte corregido (" + str(n) + " ocurrencia(s))")
        total += 1
    elif "cont.style.width='595px'" in src:
        print("* " + nombre + ": ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro la linea del ancho")

print()
ok_total = True
for nombre in ['historial.html', 'dashboard.html']:
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
    print("Listo. El reporte ya no deberia cortarse: los montos de la")
    print("derecha (ventas totales, gastos, ganancia) deben ser visibles.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
