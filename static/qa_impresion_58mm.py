#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Ajusta la impresion de tickets para la impresora termica
Xprinter XP-58IIH (papel de 58mm, area imprimible ~48mm).
 - Ancho en mm en vez de px
 - @page sin margenes (el navegador agrega margenes de hoja por defecto)
 - Fuente y espaciados reducidos para que quepa
 - Logo mas chico
Aplica a pagos.html, historial.html y devoluciones.html.
Uso: cd ~/inventario-qa/static && python3 qa_impresion_58mm.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

CSS_58 = ("@page{size:58mm auto;margin:0}"
          "body{font-family:monospace;font-size:11px;width:48mm;margin:0 auto;padding:2mm 0;line-height:1.35}"
          "img{max-width:34mm;height:auto}")

# ============================================================
# pagos.html e historial.html
# ============================================================
viejo = "<style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto}"
nuevo = "<style>" + CSS_58

for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    if viejo in src:
        src = src.replace(viejo, nuevo, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        res.append("OK " + nombre + ": impresion ajustada a 58mm")
    elif '@page{size:58mm auto' in src:
        res.append("* " + nombre + ": ya estaba ajustado")
    else:
        res.append("ERROR " + nombre + ": no se encontro el estilo de impresion")

# ============================================================
# devoluciones.html (mismo estilo, con el color forzado)
# ============================================================
ruta = os.path.join(STATIC, 'devoluciones.html')
src = open(ruta, encoding='utf-8').read()
viejo_d = "const estilos = '<style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto;color:#000}'"
nuevo_d = ("const estilos = '<style>@page{size:58mm auto;margin:0}"
           "body{font-family:monospace;font-size:11px;width:48mm;margin:0 auto;padding:2mm 0;line-height:1.35;color:#000}"
           "img{max-width:34mm;height:auto}'")
if viejo_d in src:
    src = src.replace(viejo_d, nuevo_d, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK devoluciones.html: impresion ajustada a 58mm")
elif '@page{size:58mm auto' in src:
    res.append("* devoluciones.html: ya estaba ajustado")
else:
    res.append("ERROR devoluciones.html: no se encontro el estilo de impresion")

# ============================================================
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
    print("AL IMPRIMIR DESDE EL NAVEGADOR, EN EL DIALOGO:")
    print("  - Impresora: XP-58")
    print("  - Margenes: Ninguno")
    print("  - Desmarcar 'Encabezados y pies de pagina'")
    print("  - Marcar 'Graficos de fondo' (para que salga el logo)")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
