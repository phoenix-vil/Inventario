#!/usr/bin/env python3
"""
Asigna todos los productos a una sucursal aleatoria.
Uso: python3 asignar_stock_aleatorio.py [ruta_db]
"""
import sqlite3, sys, random
from datetime import datetime

DB = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Verificar tablas
for tabla in ("productos", "sucursales", "stock_sucursal"):
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
    if not cur.fetchone():
        print(f"ERROR: tabla '{tabla}' no encontrada en {DB}")
        sys.exit(1)

# Obtener sucursales registradas
cur.execute("SELECT nombre FROM sucursales ORDER BY nombre")
sucursales = [r[0] for r in cur.fetchall()]
if not sucursales:
    print("ERROR: No hay sucursales registradas. Crea al menos una primero.")
    sys.exit(1)

# Obtener todos los productos con stock > 0
cur.execute("SELECT id, nombre, stock, stock_minimo, vendido_por_peso FROM productos WHERE stock > 0")
productos = cur.fetchall()

if not productos:
    print("No hay productos con stock disponible.")
    conn.close(); sys.exit(0)

print(f"Asignando {len(productos)} productos a {len(sucursales)} sucursal(es): {', '.join(sucursales)}")
print()

ahora = datetime.utcnow().isoformat(sep=" ")
asignados = 0
omitidos = 0

for pid, nombre, stock, stock_min, por_peso in productos:
    # Elegir sucursal aleatoria
    suc = random.choice(sucursales)

    # Asignar TODO el stock disponible a esa sucursal
    cantidad = round(stock, 3)

    # Verificar si ya tiene asignación en alguna sucursal
    cur.execute("SELECT COUNT(*) FROM stock_sucursal WHERE producto_id=? AND cantidad>0", (pid,))
    ya_asignado = cur.fetchone()[0] > 0

    if ya_asignado:
        omitidos += 1
        continue  # No sobreescribir asignaciones existentes

    # Upsert en stock_sucursal
    cur.execute("""
        INSERT INTO stock_sucursal (producto_id, sucursal, cantidad, actualizado_en)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(producto_id, sucursal) DO UPDATE SET cantidad=excluded.cantidad, actualizado_en=excluded.actualizado_en
    """, (pid, suc, cantidad, ahora))

    unidad = "kg" if por_peso else "u"
    print(f"  {nombre[:40]:40s}  → Suc. {suc}  ({cantidad} {unidad})")
    asignados += 1

conn.commit()
conn.close()

print()
print(f"✓ {asignados} productos asignados aleatoriamente.")
if omitidos:
    print(f"  {omitidos} ya tenían asignación y se omitieron (usa --forzar para sobreescribir).")
