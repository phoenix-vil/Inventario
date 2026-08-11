#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige dos problemas en el resumen del Historial (main.py ~694-699):
 1. total_vendido restaba total_devuelto -> con registros negativos
    eso descuenta DOS VECES. Se quita la resta.
 2. El filtro de metodo_pago solo reconocia efectivo/tarjeta (segunda
    copia del bug que ya se corrigio en el otro listado).
Uso: cd ~/inventario-qa && python3 qa_fix_totales_historial.py
"""
import os

MAIN = os.path.expanduser('~/inventario-qa/main.py')
src = open(MAIN, encoding='utf-8').read()
res = []

# --- 1. Quitar la resta duplicada ---
viejo = '''    ventas = query.all()
    total_vendido = round(sum(v.total - (v.total_devuelto or 0) for v in ventas), 2)'''
nuevo = '''    ventas = query.all()
    total_vendido = round(sum(v.total for v in ventas), 2)'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK: resta duplicada de total_devuelto eliminada")
elif '''    ventas = query.all()
    total_vendido = round(sum(v.total for v in ventas), 2)''' in src:
    res.append("* la resta ya estaba corregida")
else:
    res.append("ERROR: no se encontro el bloque de total_vendido")

# --- 2. Filtro de metodo de pago completo ---
viejo2 = '''    if metodo_pago in ("efectivo", "tarjeta"):
        query = query.filter(Venta.metodo_pago == metodo_pago)'''
nuevo2 = '''    if metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia"):
        query = query.filter(Venta.metodo_pago == metodo_pago)'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    res.append("OK: filtro de metodo de pago ahora reconoce los 4 metodos")
elif viejo2.replace('"tarjeta")', '"tarjeta", "credito", "transferencia")') in src:
    res.append("* el filtro ya estaba corregido")
else:
    res.append("ADVERTENCIA: no se encontro el filtro de metodo_pago con query.filter")

open(MAIN, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

print()
print("Verificacion - las 3 sumas de ventas deben quedar SIN la resta:")
for i, linea in enumerate(open(MAIN, encoding='utf-8').read().split('\n'), 1):
    if 'total_vendido = round(sum' in linea:
        marca = "  <-- REVISAR" if 'total_devuelto' in linea else "  OK"
        print("  linea " + str(i) + ": " + linea.strip() + marca)

print()
print("=" * 58)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo.")
