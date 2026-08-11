#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quita el bloqueo de "AGOTADO" que impedia agregar productos con stock 0
al carrito desde el buscador del punto de venta.
Uso: cd ~/inventario && python3 quitar_bloqueo_agregar.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

patron = re.compile(
    r"[ \t]*// Alerta si el producto está agotado\s*\n"
    r"[ \t]*if\(p\.stock<=0\)\{\s*\n"
    r"[ \t]*alert\(`[^`]*`\);\s*\n"
    r"[ \t]*return;\s*\n"
    r"[ \t]*\}\s*\n"
)

nuevo_src, n = patron.subn(
    "  // Restriccion de stock agotado desactivada: se permite agregar aunque stock sea 0\n",
    src, count=1
)

print("Bloqueo encontrado y eliminado:", n > 0)

if n:
    src = nuevo_src
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("Archivo actualizado.")
else:
    print("No se encontro el patron exacto. Revisa manualmente lineas ~347-352.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

if ok and n:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Ahora si se puede agregar cualquier producto sin importar el stock.")
elif not ok:
    print("ADVERTENCIA: desbalance de llaves, NO se reinicio el servicio.")
