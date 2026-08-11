#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega un parametro de version (?v=timestamp) a la referencia de
modern.css en todas las paginas, para forzar al navegador a traer
la copia mas reciente y no una vieja guardada en cache.
Uso: cd ~/inventario/static && python3 fix_cache_modern_css.py
"""
import os, re, time

STATIC = os.path.expanduser('~/inventario/static')
version = str(int(time.time()))

archivos = [f for f in os.listdir(STATIC) if f.endswith('.html')]
total = 0

for archivo in archivos:
    ruta = os.path.join(STATIC, archivo)
    src = open(ruta, encoding='utf-8').read()
    original = src

    # Quitar cualquier ?v= anterior para no acumular
    src = re.sub(r'(/static/modern\.css)\?v=\d+', r'\1', src)
    # Agregar el nuevo parametro de version
    src, n = re.subn(r'/static/modern\.css(?!\?)', '/static/modern.css?v=' + version, src)

    if src != original:
        open(ruta, 'w', encoding='utf-8').write(src)
        total += n
        print("OK " + archivo + ": " + str(n) + " referencia(s) actualizadas")

print()
print("Total: " + str(total) + " paginas actualizadas con la nueva version")
print("Version usada: " + version)

print()
print("=" * 55)
print("Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("Listo. Ahora el navegador SIEMPRE traera la version mas reciente de modern.css.")
