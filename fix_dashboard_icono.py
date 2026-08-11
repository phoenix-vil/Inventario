#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige el icono del boton "Inicio" en dashboard.html (se me habia olvidado
incluirla en el script anterior). Ahora revisa TODAS las paginas .html
automaticamente, sin listas fijas, para no repetir el error.
Uso: cd ~/inventario && python3 fix_dashboard_icono.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario/static')

print("Revisando TODAS las paginas .html en busca del logo grande en btn-inicio...")
archivos = [f for f in os.listdir(STATIC) if f.endswith('.html')]
total = 0

patron = re.compile(
    r'<img src="/static/logo\.png(?:\?v=\d+)?"[^>]*style="height:36px;width:auto;display:block"[^>]*>'
)
nuevo_img = '<img src="/static/icon-nav-v2.png" alt="Inicio" class="nav-icon" style="height:32px;width:32px">'

for archivo in archivos:
    ruta = os.path.join(STATIC, archivo)
    src = open(ruta, encoding='utf-8').read()
    original = src

    nueva, n = patron.subn(nuevo_img, src)
    if n > 0:
        open(ruta, 'w', encoding='utf-8').write(nueva)
        total += n
        print("   CORREGIDO " + archivo + " (" + str(n) + " icono(s))")

if total == 0:
    print("   Todas las paginas ya estaban corregidas, no se encontro nada pendiente")

print()
print("Total corregido: " + str(total))
print()
print("Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("Listo. Refresca el Dashboard (Ctrl+Shift+R / Cmd+Shift+R).")
