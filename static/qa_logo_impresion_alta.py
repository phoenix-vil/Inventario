#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Mejora la calidad del logo impreso.
Causa: el ticket usa una copia del logo reducida a 240px (creada para
aligerar el PDF). La termica imprime a 203 DPI y un logo de 34mm
necesita ~270px, por eso se veia pixelado.
Solucion: al IMPRIMIR se usa el archivo original de 900px. El PDF
sigue usando la copia ligera, para no inflar el archivo.
Uso: cd ~/inventario-qa/static && python3 qa_logo_impresion_alta.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

# Sustituye el data-url del logo por la ruta al archivo original,
# solo en el HTML que se manda a la ventana de impresion.
SWAP = "(typeof _logoCacheDataUrl!=='undefined'&&_logoCacheDataUrl?String(_logoCacheDataUrl):'@@NADA@@')"

cambios = [
    # pagos.html
    ('pagos.html',
     "win.document.write(`<html><head><title>Punto de venta · Only Enterprises</title>",
     "generarTicketHTML(ticketActual)",
     "generarTicketHTML(ticketActual).split(_logoCacheDataUrl||'@@X@@').join('/static/logo.png')"),
    # historial.html
    ('historial.html',
     "win.document.write(`<html><head><title>Historial · Only Enterprises</title>",
     "ticketHTML(ventaDetalle)",
     "ticketHTML(ventaDetalle).split(_logoCacheDataUrl||'@@X@@').join('/static/logo.png')"),
]

for nombre, ancla, viejo_call, nuevo_call in cambios:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    if ancla not in src:
        res.append("ERROR " + nombre + ": no se encontro la ventana de impresion")
        continue
    if "join('/static/logo.png')" in src:
        res.append("* " + nombre + ": ya usaba el logo en alta")
        continue
    i = src.find(ancla)
    seg = src[i:i+1200]
    if viejo_call in seg:
        seg_nuevo = seg.replace(viejo_call, nuevo_call, 1)
        src = src[:i] + seg_nuevo + src[i+1200:]
        open(ruta, 'w', encoding='utf-8').write(src)
        res.append("OK " + nombre + ": impresion usa el logo original de 900px")
    else:
        res.append("ERROR " + nombre + ": no se encontro la llamada del ticket al imprimir")

# devoluciones.html
ruta = os.path.join(STATIC, 'devoluciones.html')
src = open(ruta, encoding='utf-8').read()
viejo_d = "+ tkGenerarHTML(tkActual) + '</body></html>'"
nuevo_d = "+ tkGenerarHTML(tkActual).split(_logoCacheDataUrl||'@@X@@').join('/static/logo.png') + '</body></html>'"
if viejo_d in src:
    src = src.replace(viejo_d, nuevo_d, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK devoluciones.html: impresion usa el logo original de 900px")
elif "join('/static/logo.png')" in src:
    res.append("* devoluciones.html: ya usaba el logo en alta")
else:
    res.append("ERROR devoluciones.html: no se encontro tkImprimir")

print()
for r in res:
    print(r)

ok_total = True
print()
for nombre in ['pagos.html', 'historial.html', 'devoluciones.html']:
    s = open(os.path.join(STATIC, nombre), encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 58)
if ok_total and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print()
    print("Imprime un ticket. El logo debe verse mucho mas definido.")
    print("Si aun se ve pixelado, avisame: se puede subir a 40mm de ancho")
    print("o generar una version del logo optimizada para termica.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
