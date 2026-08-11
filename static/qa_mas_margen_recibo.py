#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Aumenta el margen/padding del recibo de abono para que el texto
no quede tan pegado a los bordes.
Uso: cd ~/inventario-qa/static && python3 qa_mas_margen_recibo.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario-qa/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src

viejo = "contenedor.style.padding = '16px';"
nuevo = "contenedor.style.padding = '16px 24px';"

n = src.count(viejo)
if n >= 1:
    src = src.replace(viejo, nuevo)
    print("OK: padding aumentado de 16px a 16px 24px (" + str(n) + " ocurrencia(s))")
    open(CLIENTES, 'w', encoding='utf-8').write(src)
elif "'16px 24px'" in src:
    print("* Ya estaba aumentado")
else:
    print("ERROR: no se encontro el padding exacto")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Deberia haber mas aire en los bordes del recibo ahora.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
