#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limpia el historial viejo pegado al cliente "Prueba" (id=1):
- Borra los 10 pagos de credito viejos (del 30 de julio, de Melanie Mendez)
- Revierte la venta #20 (regresa el stock de "Plug 1pz" y borra el registro)
Uso: cd ~/inventario && python3 limpiar_historico_cliente_prueba.py
"""
import sqlite3, os

DB = os.path.expanduser('~/inventario/inventario.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 55)
print("Este script va a:")
print("  1. Borrar los 10 pagos de credito con cliente_id=1")
print("  2. Regresar el stock de 'Plug 1pz' (+1.0)")
print("  3. Borrar la venta #20")
print("=" * 55)

resp = input("\n¿Confirmas continuar? Escribe 'si': ").strip().lower()
if resp != 'si':
    print("Cancelado. No se hizo ningun cambio.")
    conn.close()
    exit(0)

# 1. Borrar los 10 pagos de credito viejos
cur.execute("DELETE FROM pagos_credito WHERE cliente_id=1")
print("\nOK: " + str(cur.rowcount) + " pagos de credito eliminados")

# 2. Regresar stock de Plug 1pz (producto_id=2077)
cur.execute("SELECT nombre, stock FROM productos WHERE id=2077")
r = cur.fetchone()
if r:
    nuevo_stock = round(r[1] + 1.0, 3)
    cur.execute("UPDATE productos SET stock=? WHERE id=2077", (nuevo_stock,))
    print("OK: stock de '" + r[0] + "' restaurado -> " + str(nuevo_stock))
else:
    print("ADVERTENCIA: producto 2077 ya no existe, no se pudo restaurar stock")

# 3. Borrar la venta #20
cur.execute("DELETE FROM ventas WHERE id=20")
print("OK: venta #20 eliminada")

conn.commit()
conn.close()

print()
print("=" * 55)
print("Listo. El cliente 'Prueba' deberia quedar con saldo $0 y sin historial.")
print()
print("Reinicia el servicio para ver los cambios reflejados de inmediato:")
print("  sudo systemctl restart inventario")
