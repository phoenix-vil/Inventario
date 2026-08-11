#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega una precarga del logo al iniciar cada pagina, para que el
cache ya este listo desde el primer intento de compartir (no solo desde
el segundo).
Uso: cd ~/inventario-qa/static && python3 qa_precargar_logo.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
archivos = ['clientes.html', 'pagos.html', 'historial.html']

total_ok = 0
for nombre in archivos:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        print(nombre + ": no existe, se omite")
        continue
    src = open(ruta, encoding='utf-8').read()
    original = src

    if '_logoCacheDataUrl' not in src:
        print(nombre + ": ERROR, corre primero qa_fix_cache_logo.py")
        continue

    if "cargarImagenBase64('/static/logo.png').catch" in src:
        print("* " + nombre + ": ya tenia la precarga")
        continue

    # Insertar la precarga justo despues de la funcion cargarImagenBase64
    marcador = re.search(r"function cargarImagenBase64\(url\)\{.*?\n\}\n", src, re.DOTALL)
    if marcador:
        precarga = "\ncargarImagenBase64('/static/logo.png').catch(function(){});\n"
        src = src[:marcador.end()] + precarga + src[marcador.end():]
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": precarga del logo agregada")
        total_ok += 1
    else:
        print("ERROR " + nombre + ": no se encontro la funcion cargarImagenBase64")

print()
print("Total actualizado: " + str(total_ok) + " archivo(s)")
print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. Ahora el logo se precarga al abrir la pagina, asi que compartir")
print("deberia funcionar bien desde el primer intento.")
