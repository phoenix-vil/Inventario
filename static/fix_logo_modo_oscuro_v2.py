#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version 2: agrega class="brand-logo" contemplando que el src puede
llevar un sufijo de cache-busting como ?v=1234567890.
Uso: cd ~/inventario/static && python3 fix_logo_modo_oscuro_v2.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario/static')

# Ahora el patron acepta un query string opcional despues de logo.png
patron = re.compile(r'<img\s+([^>]*?src="/static/logo\.png(?:\?[^"]*)?"[^>]*?)>')

def agregar_clase(m):
    atributos = m.group(1)
    if 'brand-logo' in atributos:
        return m.group(0)
    if re.search(r'class="[^"]*"', atributos):
        nueva = re.sub(r'class="([^"]*)"', r'class="\1 brand-logo"', atributos, count=1)
        return '<img ' + nueva + '>'
    else:
        return '<img class="brand-logo" ' + atributos + '>'

archivos = [f for f in os.listdir(STATIC) if f.endswith('.html')]
total = 0

for archivo in archivos:
    ruta = os.path.join(STATIC, archivo)
    src = open(ruta, encoding='utf-8').read()
    original = src

    nueva_src, n = patron.subn(agregar_clase, src)
    if n > 0 and nueva_src != original:
        open(ruta, 'w', encoding='utf-8').write(nueva_src)
        total += n
        print("OK " + archivo + ": " + str(n) + " logo(s) actualizado(s)")

print()
print("Total: " + str(total) + " referencias de logo.png actualizadas")

print()
print("=" * 55)
if total > 0:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. El logo debe verse blanco en modo oscuro y negro en modo claro.")
else:
    print("No se encontro ningun logo para actualizar. Revisar manualmente.")
