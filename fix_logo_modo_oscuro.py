#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hace que el logo grande (logo.png) se vea blanco en modo oscuro y negro
en modo claro, invirtiendo el color automaticamente con CSS (igual que
ya se hizo con el icono pequeno de navegacion).
Uso: cd ~/inventario && python3 fix_logo_modo_oscuro.py
"""
import os, re

BASE = os.path.expanduser('~/inventario')
STATIC = os.path.join(BASE, 'static')

# ================================================================
# 1. Agregar la clase .brand-logo a modern.css (se aplica en todas
#    las paginas que ya cargan modern.css)
# ================================================================
print("1. Agregando regla .brand-logo a modern.css...")
modern_path = os.path.join(STATIC, 'modern.css')
msrc = open(modern_path, encoding='utf-8').read()

if '.brand-logo' not in msrc:
    regla = '''

/* Logo principal: negro en modo claro, blanco en modo oscuro (auto-invertido) */
.brand-logo{display:block}
@media(prefers-color-scheme:dark){
  .brand-logo{filter:invert(1)}
}
'''
    msrc = msrc.rstrip('\n') + regla
    open(modern_path, 'w', encoding='utf-8').write(msrc)
    print("   OK regla .brand-logo agregada")
else:
    print("   * Ya existia, se omite")

# ================================================================
# 2. Agregar class="brand-logo" a TODAS las etiquetas <img> que usen
#    /static/logo.png (sin lista fija de paginas, para no olvidar ninguna)
# ================================================================
print("2. Buscando usos de logo.png en todas las paginas...")
archivos = [f for f in os.listdir(STATIC) if f.endswith('.html')]
total = 0

patron = re.compile(r'<img\s+([^>]*?src="/static/logo\.png"[^>]*?)>')

def agregar_clase(m):
    atributos = m.group(1)
    if 'brand-logo' in atributos:
        return m.group(0)  # ya tiene la clase, no tocar
    if re.search(r'class="[^"]*"', atributos):
        nueva = re.sub(r'class="([^"]*)"', r'class="\1 brand-logo"', atributos, count=1)
        return '<img ' + nueva + '>'
    else:
        return '<img class="brand-logo" ' + atributos + '>'

for archivo in archivos:
    ruta = os.path.join(STATIC, archivo)
    src = open(ruta, encoding='utf-8').read()
    original = src

    nueva_src, n = patron.subn(agregar_clase, src)
    if n > 0 and nueva_src != original:
        open(ruta, 'w', encoding='utf-8').write(nueva_src)
        total += n
        print("   OK " + archivo + ": " + str(n) + " logo(s) actualizado(s)")

print("   Total: " + str(total) + " referencias de logo.png actualizadas")

print()
print("=" * 55)
print("Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("Listo. El logo debe verse blanco en modo oscuro y negro en modo claro.")
