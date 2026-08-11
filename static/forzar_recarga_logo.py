#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuerza que el navegador cargue la version nueva del logo, agregando un parametro
de version a todas las referencias (evita el cache agresivo de Safari en iOS).
Uso: cd ~/inventario/static && python3 forzar_recarga_logo.py
"""
import os, re, time

STATIC = os.path.expanduser('~/inventario/static')
version = str(int(time.time()))

print("Version de cache-busting: " + version)
print()

archivos = [f for f in os.listdir(STATIC) if f.endswith('.html')]
total = 0

for archivo in archivos:
    ruta = os.path.join(STATIC, archivo)
    src = open(ruta, encoding='utf-8').read()
    original = src

    # Quitar cualquier ?v=... anterior que ya exista, para no acumular
    src = re.sub(r'(/static/logo\.png)\?v=\d+', r'\1', src)
    # Agregar el parametro de version nuevo a TODAS las referencias de logo.png
    src = re.sub(r'/static/logo\.png(?!\?)', '/static/logo.png?v=' + version, src)

    if src != original:
        cambios = len(re.findall(r'/static/logo\.png\?v=' + version, src))
        open(ruta, 'w', encoding='utf-8').write(src)
        total += cambios
        print("OK " + archivo + ": " + str(cambios) + " referencia(s) actualizadas")

print()
print("Total: " + str(total) + " referencias con cache-busting agregado")
print()
print("Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("Listo. Ahora SI debe verse el logo nuevo (ya no depende del cache del navegador).")
