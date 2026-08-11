#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Lleva el mismo criterio de Cotizaciones (3 resultados visibles,
scroll para ver el resto) al buscador de productos de Punto de Venta.
Uso: cd ~/inventario-qa/static && python3 qa_scroll_resultados_pagos.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()

viejo = ".resultados{display:flex;flex-direction:column;gap:6px;margin-bottom:1rem}"
nuevo = ".resultados{display:flex;flex-direction:column;gap:6px;margin-bottom:1rem;max-height:200px;overflow-y:auto}"

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("OK: buscador de Punto de Venta limitado a ~3 resultados visibles con scroll")
elif 'max-height:200px;overflow-y:auto' in src:
    print("* Ya estaba aplicado")
else:
    print("ERROR: no se encontro la regla .resultados exacta (coincidencias: " + str(n) + ")")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok:
    print("Este cambio es solo CSS, no requiere reiniciar el servicio.")
    print("Prueba directamente con Ctrl+Shift+R en Punto de Venta.")
else:
    print("ADVERTENCIA: desbalance de llaves. Revisar antes de continuar.")
