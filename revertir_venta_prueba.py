#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revierte una venta de prueba: restaura el stock de los productos
vendidos y borra el registro de la venta. Pide confirmacion explicita
antes de hacer cualquier cambio.

Uso:
  cd ~/inventario
  python3 revertir_venta_prueba.py           # usa la ULTIMA venta creada
  python3 revertir_venta_prueba.py 16        # usa la venta con ese ID especifico
"""
import sqlite3, sys, json, os

DB = os.path.expanduser('~/inventario/inventario.db')

venta_id = None
if len(sys.argv) > 1:
    try:
        venta_id = int(sys.argv[1])
    except ValueError:
        print("El id de venta debe ser un numero. Ejemplo: python3 revertir_venta_prueba.py 16")
        sys.exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

if venta_id:
    cur.execute("SELECT * FROM ventas WHERE id=?", (venta_id,))
else:
    cur.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 1")

row = cur.fetchone()
if not row:
    print("No se encontro ninguna venta" + (" con ese ID" if venta_id else ""))
    sys.exit(1)

venta = dict(row)
detalle = json.loads(venta['detalle_json'])

print("=" * 55)
print("VENTA A REVERTIR:")
print("  ID:", venta['id'])
print("  Fecha:", venta['creado_en'])
print("  Operador:", venta.get('operador'))
print("  Sucursal:", venta.get('sucursal'))
print("  Metodo de pago:", venta['metodo_pago'])
print("  Total: $" + str(venta['total']))
if venta['metodo_pago'] == 'credito' and venta.get('cliente_id'):
    print("  Cliente (credito) ID:", venta['cliente_id'])
print()
print("Productos que recuperaran su stock:")
for item in detalle:
    print("  - " + item['nombre'] + "  x" + str(item['cantidad']))
print("=" * 55)

resp = input("\n¿Confirmas BORRAR esta venta y regresar el stock? Escribe 'si' para continuar: ").strip().lower()
if resp != 'si':
    print("Cancelado. No se hizo ningun cambio.")
    conn.close()
    sys.exit(0)

print()
for item in detalle:
    cur.execute("SELECT nombre, stock FROM productos WHERE id=?", (item['producto_id'],))
    r = cur.fetchone()
    if r:
        nuevo_stock = round(r['stock'] + item['cantidad'], 3)
        cur.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, item['producto_id']))
        print("OK stock restaurado: " + r['nombre'] + " -> " + str(nuevo_stock))
    else:
        print("ADVERTENCIA: el producto id " + str(item['producto_id']) + " ya no existe, no se pudo restaurar su stock")

cur.execute("DELETE FROM ventas WHERE id=?", (venta['id'],))
conn.commit()
conn.close()

print()
print("=" * 55)
print("Listo. Venta #" + str(venta['id']) + " eliminada y stock restaurado.")
if venta['metodo_pago'] == 'credito' and venta.get('cliente_id'):
    print()
    print("NOTA: esta era una venta a credito. El saldo del cliente ya deberia")
    print("quedar en $0 (o lo que tuviera antes). Si el cliente era de PRUEBA")
    print("y quieres borrarlo tambien, hazlo desde Menu -> Clientes -> tocalo -> Eliminar")
    print("(el boton solo deja borrar si el saldo ya es 0).")
print()
print("Reinicia el servicio para ver los cambios reflejados de inmediato:")
print("  sudo systemctl restart inventario")
