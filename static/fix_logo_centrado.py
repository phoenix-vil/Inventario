#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige el centrado del logo: al ponerlo display:block (necesario para
que el filtro de inversion de color funcione bien), dejo de respetar
el text-align:center del contenedor. Se arregla con margin:0 auto.
Uso: cd ~/inventario/static && python3 fix_logo_centrado.py
"""
import os, re, time

STATIC = os.path.expanduser('~/inventario/static')
modern_path = os.path.join(STATIC, 'modern.css')
src = open(modern_path, encoding='utf-8').read()
original = src

viejo = '.brand-logo{display:block}'
nuevo = '.brand-logo{display:block;margin-left:auto;margin-right:auto}'

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("OK: margin:auto agregado a .brand-logo para centrarlo")
elif 'margin-left:auto' in src and '.brand-logo' in src:
    print("* Ya estaba corregido")
else:
    print("ERROR: no se encontro la regla exacta .brand-logo{display:block}")

if src != original:
    open(modern_path, 'w', encoding='utf-8').write(src)
    print("Archivo guardado.")

# Actualizar tambien la version de cache-busting para forzar la recarga
print()
print("Actualizando version de cache-busting de modern.css...")
version = str(int(time.time()))
archivos = [f for f in os.listdir(STATIC) if f.endswith('.html')]
total = 0
for archivo in archivos:
    ruta = os.path.join(STATIC, archivo)
    s = open(ruta, encoding='utf-8').read()
    o = s
    s = re.sub(r'(/static/modern\.css)\?v=\d+', r'\1', s)
    s, n2 = re.subn(r'/static/modern\.css(?!\?)', '/static/modern.css?v=' + version, s)
    if s != o:
        open(ruta, 'w', encoding='utf-8').write(s)
        total += n2
print("Version actualizada en " + str(total) + " paginas: " + version)

print()
print("=" * 55)
print("Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("Listo. El logo deberia verse centrado ahora.")
