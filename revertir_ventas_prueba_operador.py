#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca y revierte TODAS las ventas de un operador especifico (por defecto
"prueba"): regresa el stock de cada producto vendido y borra el registro
de la venta. Muestra todo antes de tocar nada, pide confirmacion explicita.

Uso:
  cd ~/inventario
  python3 revertir_ventas_prueba_operador.py            # busca operador "prueba"
  python3 revertir_ventas_prueba_operador.py "Prueba"    # busca otro nombre exacto
"""
import sqlite3, sys, json, os

DB = os.path.expanduser('~/inventario/inventario.db')
operador_buscar = sys.argv[1] if len(sys.argv) > 1 else 'prueba'

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM ventas WHERE operador=? ORDER BY id", (operador_buscar,))
ventas = cur.fetchall()

if not ventas:
    print("No se encontraron ventas con el operador '" + operador_buscar + "'")
    conn.close()
    sys.exit(0)

print("=" * 55)
print("VENTAS ENCONTRADAS con operador '" + operador_buscar + "':")
print("=" * 55)
detalles_por_venta = {}
for v in ventas:
    detalle = json.loads(v['detalle_json'])
    detalles_por_venta[v['id']] = detalle
    print()
    print("Venta #" + str(v['id']) + "  |  " + str(v['creado_en']) + "  |  Total: $" + str(v['total']) + "  |  Sucursal: " + str(v['sucursal']))
    for item in detalle:
        print("    - " + item['nombre'] + "  x" + str(item['cantidad']))

print()
print("=" * 55)
print("Total de ventas a revertir: " + str(len(ventas)))
print("=" * 55)

resp = input("\n¿Confirmas BORRAR estas " + str(len(ventas)) + " ventas y regresar su stock? Escribe 'si' para continuar: ").strip().lower()
if resp != 'si':
    print("Cancelado. No se hizo ningun cambio.")
    conn.close()
    sys.exit(0)

print()
for v in ventas:
    detalle = detalles_por_venta[v['id']]
    print("--- Revirtiendo venta #" + str(v['id']) + " ---")
    for item in detalle:
        cur.execute("SELECT nombre, stock FROM productos WHERE id=?", (item['producto_id'],))
        r = cur.fetchone()
        if r:
            nuevo_stock = round(r['stock'] + item['cantidad'], 3)
            cur.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, item['producto_id']))
            print("  OK stock restaurado: " + r['nombre'] + " -> " + str(nuevo_stock))
        else:
            print("  ADVERTENCIA: producto id " + str(item['producto_id']) + " ya no existe")
    cur.execute("DELETE FROM ventas WHERE id=?", (v['id'],))
    print("  OK venta #" + str(v['id']) + " eliminada")

conn.commit()
conn.close()

print()
print("=" * 55)
print("Listo. " + str(len(ventas)) + " venta(s) revertida(s) y stock restaurado.")
print()
print("Reinicia el servicio para ver los cambios reflejados de inmediato:")
print("  sudo systemctl restart inventario")
