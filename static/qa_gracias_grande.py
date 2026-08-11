#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Pone "Gracias por su compra!" un poco mas grande y en negritas.
Uso: cd ~/inventario-qa/static && python3 qa_gracias_grande.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo = '''  y+=15;
  doc.setFont('courier','normal'); doc.setFontSize(9); doc.setTextColor(0);
  doc.text('¡Gracias por su compra!', centerX, y, {align:'center'});'''

nuevo = '''  y+=15;
  doc.setFont('courier','bold'); doc.setFontSize(11); doc.setTextColor(0);
  doc.text('¡Gracias por su compra!', centerX, y, {align:'center'});'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": Gracias por su compra ahora es mas grande y negrita")
        total += 1
    elif "fontSize(11); doc.setTextColor(0);\n  doc.text('¡Gracias" in src:
        print("* " + nombre + ": ya estaba corregido")
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
    print("Listo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
