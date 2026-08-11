#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Hace que "Imprimir" abra el MISMO PDF (generarPDFTicketVenta) que
usan Descargar y WhatsApp, en vez de su propio render HTML aparte.
Uso: cd ~/inventario-qa/static && python3 qa_imprimir_mismo_pdf.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo_pagos = '''function imprimirTicket(){
  if(!ticketActual)return;
  const win=window.open('','_blank');
  win.document.write(`<html><head><title>Punto de venta · Only Enterprises</title>
    <style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto}
    .tk-line{display:flex;justify-content:space-between;margin-bottom:3px}
    .tk-total{font-weight:bold;font-size:15px;margin-top:6px;padding-top:6px}
    .tk-desc{color:#a32d2d}.tk-ahorro{color:#3b6d11;font-weight:bold}.tk-head,.tk-foot{text-align:center;margin:8px 0}
    .tk-negocio{font-size:18px;font-weight:bold}.tk-items{padding:6px 0;margin:6px 0}
    </style></head><body>${generarTicketHTML(ticketActual)}</body></html>`);
  win.document.close();
  setTimeout(()=>win.print(),300);
}'''

nuevo_pagos = '''async function imprimirTicket(){
  if(!ticketActual)return;
  const blob = await generarPDFTicketVenta(ticketActual);
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}'''

ruta_pagos = os.path.join(STATIC, 'pagos.html')
src = open(ruta_pagos, encoding='utf-8').read()
n1 = src.count(viejo_pagos)
if n1 == 1:
    src = src.replace(viejo_pagos, nuevo_pagos, 1)
    open(ruta_pagos, 'w', encoding='utf-8').write(src)
    print("OK pagos.html: imprimirTicket() ahora abre el mismo PDF")
elif 'window.open(url, \'_blank\')' in src:
    print("* pagos.html: ya estaba actualizado")
else:
    print("ERROR pagos.html: no se encontro el bloque exacto (coincidencias: " + str(n1) + ")")

viejo_hist = '''function imprimirDetalle(){
  if(!ventaDetalle)return;
  const win=window.open('','_blank');
  win.document.write(`<html><head><title>Historial · Only Enterprises</title>
    <style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto}
    .tk-line{display:flex;justify-content:space-between;margin-bottom:3px}
    .tk-total{font-weight:bold;font-size:15px;margin-top:6px;padding-top:6px}
    .tk-desc{color:#a32d2d}.tk-ahorro{color:#3b6d11;font-weight:bold}.tk-head,.tk-foot{text-align:center;margin:8px 0}
    .tk-negocio{font-size:18px;font-weight:bold}.tk-items{padding:6px 0;margin:6px 0}
    </style></head><body>${ticketHTML(ventaDetalle)}</body></html>`);
  win.document.close();
  setTimeout(()=>win.print(),300);
}'''

nuevo_hist = '''async function imprimirDetalle(){
  if(!ventaDetalle)return;
  const blob = await generarPDFTicketVenta(ventaDetalle);
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}'''

ruta_hist = os.path.join(STATIC, 'historial.html')
src2 = open(ruta_hist, encoding='utf-8').read()
n2 = src2.count(viejo_hist)
if n2 == 1:
    src2 = src2.replace(viejo_hist, nuevo_hist, 1)
    open(ruta_hist, 'w', encoding='utf-8').write(src2)
    print("OK historial.html: imprimirDetalle() ahora abre el mismo PDF")
elif 'window.open(url, \'_blank\')' in src2:
    print("* historial.html: ya estaba actualizado")
else:
    print("ERROR historial.html: no se encontro el bloque exacto (coincidencias: " + str(n2) + ")")

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
    print("Listo. Imprimir ahora abre el mismo PDF en una pestana nueva --")
    print("desde ahi usas el boton de imprimir propio del visor de PDF del navegador.")
    print("Sera exactamente el mismo diseno que Descargar y WhatsApp, siempre.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
