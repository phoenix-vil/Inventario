#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Cambia el favicon de la pestana: usa icon-nav-v2.png (que ya tiene
fondo transparente) en vez del touch-icon con fondo blanco.
Ademas genera una version blanca del icono para tema oscuro y las
enlaza con media queries, para que el simbolo se vea en ambos temas.
Uso: cd ~/inventario-qa/static && python3 qa_favicon_transparente.py
"""
import os, re, glob
from PIL import Image

STATIC = os.path.expanduser('~/inventario-qa/static')

# ============================================================
# 1. Generar version blanca del icono (para tema oscuro)
# ============================================================
origen = os.path.join(STATIC, 'icon-nav-v2.png')
destino_blanco = os.path.join(STATIC, 'icon-nav-blanco.png')

im = Image.open(origen).convert('RGBA')
pixeles = im.load()
ancho, alto = im.size
for x in range(ancho):
    for y in range(alto):
        r, g, b, a = pixeles[x, y]
        if a > 0:
            pixeles[x, y] = (255, 255, 255, a)
im.save(destino_blanco)
print("OK: icon-nav-blanco.png generado (version blanca para tema oscuro)")

# ============================================================
# 2. Reemplazar el favicon en todos los HTML
# ============================================================
nuevas_etiquetas = (
    '<link rel="icon" type="image/png" href="/static/icon-nav-v2.png" media="(prefers-color-scheme: light)">\n'
    '<link rel="icon" type="image/png" href="/static/icon-nav-blanco.png" media="(prefers-color-scheme: dark)">'
)

print()
for ruta in sorted(glob.glob(os.path.join(STATIC, '*.html'))):
    nombre = os.path.basename(ruta)
    src = open(ruta, encoding='utf-8').read()
    original = src

    if 'icon-nav-blanco.png' in src:
        print("* " + nombre + ": ya estaba actualizado")
        continue

    # Reemplazar la etiqueta de icono existente (rel="icon", no apple-touch-icon)
    patron = re.compile(r'<link rel="icon"[^>]*>')
    m = patron.search(src)
    if m:
        src = patron.sub(nuevas_etiquetas, src, count=1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": favicon transparente con soporte de tema")
    else:
        print("* " + nombre + ": no tenia etiqueta de favicon")

print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. El icono de la pestana ahora es transparente y cambia")
print("de color segun el tema del navegador.")
print()
print("NOTA: los navegadores cachean el favicon de forma agresiva.")
print("Si no ves el cambio, cierra la pestana por completo y vuelve a abrirla,")
print("o prueba en una ventana de incognito.")
