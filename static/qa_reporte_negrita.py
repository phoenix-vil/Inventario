#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Pone en negrita el texto del reporte PDF. El color ya era negro
puro (0,0,0); lo que se veia tenue es el grosor de Courier normal.
Uso: cd ~/inventario-qa/static && python3 qa_reporte_negrita.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

reemplazos = [
    # fila(): el texto normal pasa a negrita
    ("""    doc.setFont('courier', bold ? 'bold' : 'normal');
    doc.setFontSize(size || 10);""",
     """    doc.setFont('courier','bold');
    doc.setFontSize(size || 10);"""),
    # "Sin ventas en el periodo" / "Sin movimientos"
    ("""    doc.setFont('courier','normal'); doc.setFontSize(10);
    doc.text('Sin ventas en el período', M, y); y += 16;""",
     """    doc.setFont('courier','bold'); doc.setFontSize(10);
    doc.text('Sin ventas en el período', M, y); y += 16;"""),
    ("""    doc.setFont('courier','normal'); doc.setFontSize(10);
    doc.text('Sin movimientos de crédito en el período', M, y); y += 16;""",
     """    doc.setFont('courier','bold'); doc.setFontSize(10);
    doc.text('Sin movimientos de crédito en el período', M, y); y += 16;"""),
    # subtitulo de periodo y fecha de generado
    ("""  doc.setFont('courier','normal'); doc.setFontSize(10);
  doc.text(etiquetaPeriodo || '', W/2, y, {align:'center'}); y += 14;""",
     """  doc.setFont('courier','bold'); doc.setFontSize(10);
  doc.text(etiquetaPeriodo || '', W/2, y, {align:'center'}); y += 14;"""),
    # filas de la tabla de clientes
    ("""    doc.setFont('courier','normal');
    d.clientes_detalle.forEach(function(c){""",
     """    doc.setFont('courier','bold');
    d.clientes_detalle.forEach(function(c){"""),
    ("""      const nombreCorto = doc.splitTextToSize(c.nombre, 190)[0];
      doc.setFont('courier','normal'); doc.setFontSize(9);""",
     """      const nombreCorto = doc.splitTextToSize(c.nombre, 190)[0];
      doc.setFont('courier','bold'); doc.setFontSize(9);"""),
]

for nombre in ['historial.html', 'dashboard.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    original = src
    aplicados = 0
    for viejo, nuevo in reemplazos:
        if viejo in src:
            src = src.replace(viejo, nuevo, 1)
            aplicados += 1

    if src != original:
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": " + str(aplicados) + " de " + str(len(reemplazos)) + " bloques puestos en negrita")
    else:
        print("* " + nombre + ": sin cambios (puede que ya estuviera en negrita)")

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
    print("Listo. El texto del reporte ahora es mas solido y legible.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
