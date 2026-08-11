#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Oscurece el texto gris del ticket (sucursal, fecha, operador) para
que se lea mejor: tanto en pantalla/impresion (CSS .tk-sub) como en el PDF.
Aplica a pagos.html y historial.html.
Uso: cd ~/inventario-qa/static && python3 qa_oscurecer_texto_ticket.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

# ================================================================
# 1. CSS .tk-sub: de var(--text2) [gris] a var(--text) [oscuro/negro]
# ================================================================
viejo_css = '.tk-sub{font-size:12px;color:var(--text2)}'
nuevo_css = '.tk-sub{font-size:12px;color:var(--text)}'

total_css = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo_css)
    if n == 1:
        src = src.replace(viejo_css, nuevo_css, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": .tk-sub ahora usa el mismo tono oscuro")
        total_css += 1
    elif '.tk-sub{font-size:12px;color:var(--text)}' in src:
        print("* " + nombre + ": CSS ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro la regla .tk-sub exacta")

print()

# ================================================================
# 2. PDF: encabezado (Sucursal/Ticket/fecha/Operador) de gris(120) a
#    oscuro(40) -- se mantiene un poco mas suave que el 20 del total,
#    para conservar jerarquia visual, pero mucho mas legible que 120
# ================================================================
viejo_pdf = '''  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(120);
  const fecha = new Date(v.fecha).toLocaleString('es-MX');
  if(v.sucursal){ doc.text('Sucursal '+v.sucursal, centerX, y, {align:'center'}); y+=13; }
  doc.text('Ticket de venta #'+v.id, centerX, y, {align:'center'}); y+=13;
  doc.text(fecha, centerX, y, {align:'center'}); y+=13;
  if(v.operador){ doc.text('Operador: '+v.operador, centerX, y, {align:'center'}); y+=13; }'''

nuevo_pdf = '''  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(40);
  const fecha = new Date(v.fecha).toLocaleString('es-MX');
  if(v.sucursal){ doc.text('Sucursal '+v.sucursal, centerX, y, {align:'center'}); y+=13; }
  doc.text('Ticket de venta #'+v.id, centerX, y, {align:'center'}); y+=13;
  doc.text(fecha, centerX, y, {align:'center'}); y+=13;
  if(v.operador){ doc.text('Operador: '+v.operador, centerX, y, {align:'center'}); y+=13; }'''

total_pdf = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo_pdf)
    if n == 1:
        src = src.replace(viejo_pdf, nuevo_pdf, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": encabezado del PDF oscurecido")
        total_pdf += 1
    elif "setTextColor(40)" in src:
        print("* " + nombre + ": PDF ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto del PDF")

# ================================================================
# Verificar y reiniciar
# ================================================================
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
    print("Listo. El texto de sucursal/fecha/operador ahora se lee mucho mejor,")
    print("tanto en pantalla, como al imprimir, como en el PDF descargado.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
