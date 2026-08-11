#!/usr/bin/env python3
"""
Importa los productos reales del inventario y borra todos los artículos de prueba.
Uso: python3 importar_inventario.py [ruta_db]

El archivo productos_real.csv debe estar en el mismo directorio.
"""
import sqlite3, csv, sys, os
from datetime import datetime

DB     = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
CSV_IN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "productos_real.csv")

# ── Verificaciones ─────────────────────────────────────────────────────────
if not os.path.exists(DB):
    print(f"ERROR: No se encontró la base de datos en '{DB}'")
    print("       Corre el script desde ~/inventario/ o pasa la ruta como argumento.")
    sys.exit(1)

if not os.path.exists(CSV_IN):
    print(f"ERROR: No se encontró '{CSV_IN}'")
    print("       Asegúrate de que productos_real.csv esté en el mismo directorio.")
    sys.exit(1)

# ── Leer CSV ───────────────────────────────────────────────────────────────
with open(CSV_IN, newline='', encoding='utf-8') as f:
    productos = list(csv.DictReader(f))

if not productos:
    print("ERROR: El CSV está vacío.")
    sys.exit(1)

print(f"Productos en CSV: {len(productos)}")

# ── Confirmación ───────────────────────────────────────────────────────────
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM productos")
actuales = cur.fetchone()[0]
print(f"Productos actuales en la base de datos: {actuales}")
print()
if actuales > 0:
    resp = input(f"⚠️  Se borrarán los {actuales} productos existentes (pruebas) y se importarán {len(productos)} reales. ¿Continuar? (s/N): ").strip().lower()
    if resp != 's':
        print("Cancelado.")
        conn.close()
        sys.exit(0)

# ── Borrar productos de prueba y datos relacionados ────────────────────────
cur.execute("SELECT id FROM productos")
ids_existentes = [r[0] for r in cur.fetchall()]
if ids_existentes:
    ph = ','.join('?' * len(ids_existentes))
    cur.execute(f"DELETE FROM stock_sucursal WHERE producto_id IN ({ph})", ids_existentes)
    cur.execute("DELETE FROM ventas")          # Las ventas de prueba ya no tienen sentido
    cur.execute("DELETE FROM productos")
    print(f"✓ {len(ids_existentes)} productos de prueba eliminados")
    print(f"✓ Historial de ventas de prueba eliminado")

# ── Importar productos reales ──────────────────────────────────────────────
ahora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
insertados = 0
sin_precio = 0

for p in productos:
    nombre       = p['nombre'].strip()
    categoria    = p['categoria'].strip() or 'General'
    marca        = p['marca'].strip() or None
    codigo       = p['codigo_barras'].strip() or None
    precio_venta = float(p['precio_venta'] or 0)
    precio_costo = float(p['precio_costo'] or 0)
    stock        = float(p['stock'] or 0)
    stock_minimo = float(p['stock_minimo'] or 0)

    if precio_venta <= 0:
        sin_precio += 1
        precio_venta = precio_costo  # Usar costo como precio si no tiene precio de venta

    try:
        cur.execute("""
            INSERT INTO productos
              (nombre, categoria, marca, codigo_barras,
               precio_venta, precio_costo, stock, stock_minimo,
               unidad, vendido_por_peso, descuento_pct,
               creado_en, actualizado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (nombre, categoria, marca, codigo,
              precio_venta, precio_costo, stock, stock_minimo,
              'pieza', 0, 0.0, ahora, ahora))
        insertados += 1
    except sqlite3.IntegrityError:
        # Código de barras duplicado: insertar sin código
        cur.execute("""
            INSERT INTO productos
              (nombre, categoria, marca, codigo_barras,
               precio_venta, precio_costo, stock, stock_minimo,
               unidad, vendido_por_peso, descuento_pct,
               creado_en, actualizado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (nombre, categoria, marca, None,
              precio_venta, precio_costo, stock, stock_minimo,
              'pieza', 0, 0.0, ahora, ahora))
        insertados += 1

conn.commit()

# ── Resumen ────────────────────────────────────────────────────────────────
total_db   = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
total_cats = conn.execute("SELECT COUNT(DISTINCT categoria) FROM productos").fetchone()[0]
total_marc = conn.execute("SELECT COUNT(DISTINCT marca) FROM productos WHERE marca IS NOT NULL").fetchone()[0]
conn.close()

print()
print(f"✓ {insertados} productos importados correctamente")
if sin_precio:
    print(f"  {sin_precio} productos usaron precio_costo como precio de venta (no tenían precio)")
print()
print(f"Base de datos final:")
print(f"  Productos: {total_db}")
print(f"  Categorías (marcas): {total_cats}")
print(f"  Marcas únicas: {total_marc}")
print()
print("✅ ¡Listo! Reinicia el servicio para refrescar la app:")
print("   sudo systemctl restart inventario")
