#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Corrige el recorte del PDF: fuerza orientacion portrait y una
altura minima mayor al ancho, para que jsPDF no lo confunda con apaisado.
2. Agrega el logo real (imagen) a generarTicketHTML/ticketHTML, usado
tanto en pantalla como al imprimir.
Aplica a pagos.html y historial.html.
Uso: cd ~/inventario-qa/static && python3 qa_fix_pdf_recorte_y_logo_print.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

# ================================================================
# Parte 1: corregir la orientacion/altura minima del PDF
# ================================================================
viejo_pdf = '''  let alturaEstimada = 260 + numItems * 15;
  if(v.descuento_extra_pct>0) alturaEstimada += 36;
  const ahorroTk0 = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk0>0.005) alturaEstimada += 18;

  const doc = new jsPDFCtor({ unit:'pt', format:[320, alturaEstimada] });'''

nuevo_pdf = '''  let alturaEstimada = 260 + numItems * 15;
  if(v.descuento_extra_pct>0) alturaEstimada += 36;
  const ahorroTk0 = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk0>0.005) alturaEstimada += 18;
  alturaEstimada = Math.max(alturaEstimada, 340);

  const doc = new jsPDFCtor({ unit:'pt', format:[320, alturaEstimada], orientation:'portrait' });'''

total_pdf = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        continue
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo_pdf)
    if n == 1:
        src = src.replace(viejo_pdf, nuevo_pdf, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": PDF forzado a portrait, altura minima 340")
        total_pdf += 1
    elif "orientation:'portrait'" in src:
        print("* " + nombre + ": ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto del PDF")

print()

# ================================================================
# Parte 2: agregar el logo real (imagen) al HTML de pantalla/impresion
# ================================================================
viejo_html_pagos = '''function generarTicketHTML(v){
  const fecha=new Date(v.fecha).toLocaleString('es-MX');
  let html=`<div class="tk-head">
    <div class="tk-negocio">Only Enterprises</div>'''

nuevo_html_pagos = '''function generarTicketHTML(v){
  const fecha=new Date(v.fecha).toLocaleString('es-MX');
  const logoSrc=_logoCacheDataUrl||'/static/logo.png';
  let html=`<div class="tk-head">
    <img src="${logoSrc}" alt="Only Enterprises" style="height:44px;width:auto;margin-bottom:6px">'''

ruta_pagos = os.path.join(STATIC, 'pagos.html')
src = open(ruta_pagos, encoding='utf-8').read()
n = src.count(viejo_html_pagos)
if n == 1:
    src = src.replace(viejo_html_pagos, nuevo_html_pagos, 1)
    open(ruta_pagos, 'w', encoding='utf-8').write(src)
    print("OK pagos.html: logo real agregado a generarTicketHTML (pantalla + imprimir)")
elif 'logoSrc=_logoCacheDataUrl' in src:
    print("* pagos.html: ya estaba corregido")
else:
    print("ERROR pagos.html: no se encontro generarTicketHTML exacto")

viejo_html_hist = '''function ticketHTML(v){
  const fecha=new Date(v.fecha).toLocaleString('es-MX');
  let html=`<div class="tk-head">
    <div class="tk-negocio">Only Enterprises</div>'''

nuevo_html_hist = '''function ticketHTML(v){
  const fecha=new Date(v.fecha).toLocaleString('es-MX');
  const logoSrc=_logoCacheDataUrl||'/static/logo.png';
  let html=`<div class="tk-head">
    <img src="${logoSrc}" alt="Only Enterprises" style="height:44px;width:auto;margin-bottom:6px">'''

ruta_hist = os.path.join(STATIC, 'historial.html')
src2 = open(ruta_hist, encoding='utf-8').read()
n2 = src2.count(viejo_html_hist)
if n2 == 1:
    src2 = src2.replace(viejo_html_hist, nuevo_html_hist, 1)
    open(ruta_hist, 'w', encoding='utf-8').write(src2)
    print("OK historial.html: logo real agregado a ticketHTML (pantalla + imprimir)")
elif 'logoSrc=_logoCacheDataUrl' in src2:
    print("* historial.html: ya estaba corregido")
else:
    print("ERROR historial.html: no se encontro ticketHTML exacto")

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
    print("Listo. El PDF ya no deberia recortarse, y el logo real aparece")
    print("tanto en pantalla como al imprimir.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
