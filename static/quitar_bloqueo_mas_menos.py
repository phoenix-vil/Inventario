#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quita el bloqueo de stock que quedaba en los botones +/- de cantidad
del carrito (cambiarCantidad), tanto para productos normales como por peso.
Uso: cd ~/inventario && python3 quitar_bloqueo_mas_menos.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# --- Caso "por peso" ---
patron_peso = re.compile(
    r"if\(delta>0 && c\.stock!=null && nuevo>c\.stock\)\{\s*"
    r"alert\(`[^`]*`\);\s*"
    r"return;\s*"
    r"\}\s*"
)
src, n1 = patron_peso.subn("", src)

# --- Caso "por pieza" ---
patron_pieza = re.compile(
    r"if\(delta>0 && c\.stock!=null && c\.cantidad\+1>c\.stock\)\{\s*"
    r"alert\(`[^`]*`\);\s*"
    r"return;\s*"
    r"\}\s*"
)
src, n2 = patron_pieza.subn("", src)

print("Bloqueo 'por peso' eliminado:", n1 > 0)
print("Bloqueo 'por pieza' eliminado:", n2 > 0)

if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("\nArchivo actualizado.")
else:
    print("\nNo se encontro ningun patron, no se modifico nada.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

if ok and (n1 or n2):
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Los botones +/- ya no bloquean por falta de stock.")
elif not ok:
    print("ADVERTENCIA: desbalance de llaves detectado, NO se reinicio el servicio.")
