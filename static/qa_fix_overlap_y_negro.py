#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige dos problemas reales del PDF:
1. Nombres largos de producto se encimaban con la siguiente linea
   (no se contaba el alto extra cuando el texto se envolvia a 2 lineas).
2. El texto se veia muy claro/delgado -- se pone en negrita para que
   se lea mejor, sin perder legibilidad.
Uso: cd ~/inventario-qa/static && python3 qa_fix_overlap_y_negro.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo_items = '''  doc.setFontSize(9);
  (v.detalle||[]).forEach(function(it){
    const cant = Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    doc.setTextColor(0);
    doc.text(cant+' '+it.nombre, 24, y, {maxWidth:190});
    doc.text(money(it.importe), 296, y, {align:'right'});
    y+=15;
  });'''

nuevo_items = '''  doc.setFont('courier','bold'); doc.setFontSize(9);
  (v.detalle||[]).forEach(function(it){
    const cant = Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    doc.setTextColor(0);
    const textoItem = cant+' '+it.nombre;
    const lineasItem = doc.splitTextToSize(textoItem, 190);
    doc.text(lineasItem, 24, y);
    doc.text(money(it.importe), 296, y, {align:'right'});
    y += 13 * lineasItem.length + 2;
  });'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo_items)
    if n == 1:
        src = src.replace(viejo_items, nuevo_items, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": envoltura de texto corregida (sin encimar)")
        total += 1
    elif 'splitTextToSize' in src:
        print("* " + nombre + ": ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

print()

# Tambien poner en negrita el resto del texto del cuerpo (Sucursal, fecha,
# Pago, Pago con, Cambio, etc) para que se vea mas solido/visible
reemplazos_negrita = [
    ("doc.setFont('courier','normal'); doc.setFontSize(9); doc.setTextColor(0);\n  const fecha",
     "doc.setFont('courier','bold'); doc.setFontSize(9); doc.setTextColor(0);\n  const fecha"),
    ("  doc.setFont('courier','normal'); doc.setFontSize(9); doc.setTextColor(0);\n  if(v.metodo_pago==='credito'){",
     "  doc.setFont('courier','bold'); doc.setFontSize(9); doc.setTextColor(0);\n  if(v.metodo_pago==='credito'){"),
]

for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    cambiado = False
    for viejo_r, nuevo_r in reemplazos_negrita:
        if viejo_r in src:
            src = src.replace(viejo_r, nuevo_r)
            cambiado = True
    if cambiado:
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": texto de encabezado/pago puesto en negrita para mas visibilidad")

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
    print("Listo. Los nombres largos ya no se encimaran, y el texto")
    print("se ve mas solido/visible en negrita.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
