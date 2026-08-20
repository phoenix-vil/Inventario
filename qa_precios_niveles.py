"""Agrega los precios por nivel y la separación de clientes por sucursal.

    python3 qa_precios_niveles.py inventario.db [sucursal_clientes_actuales] [sucursales_con_niveles...]

Sin el segundo argumento, los clientes existentes se quedan sin sucursal, o sea
visibles desde todas. Idempotente.
"""
import sqlite3
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
sucursal_actual = sys.argv[2] if len(sys.argv) > 2 else None

c = sqlite3.connect(ruta)

def agregar(tabla, columna, tipo):
    if columna in [r[1] for r in c.execute("pragma table_info(%s)" % tabla)]:
        print("  ya existía: %s.%s" % (tabla, columna))
        return False
    c.execute("ALTER TABLE %s ADD COLUMN %s %s" % (tabla, columna, tipo))
    print("  agregada:   %s.%s" % (tabla, columna))
    return True

for col in ("precio_1", "precio_2", "precio_3"):
    agregar("productos", col, "FLOAT")
agregar("sucursales", "usa_niveles_precio", "BOOLEAN DEFAULT 0")
agregar("clientes", "sucursal", "VARCHAR")
agregar("clientes", "nivel_precio", "INTEGER")
c.execute("CREATE INDEX IF NOT EXISTS ix_clientes_sucursal ON clientes (sucursal)")
c.commit()

if sucursal_actual:
    n = c.execute("UPDATE clientes SET sucursal = ? WHERE sucursal IS NULL", (sucursal_actual,)).rowcount
    c.commit()
    print("\n  %d clientes sin sucursal asignados a %s" % (n, sucursal_actual))

if len(sys.argv) > 3:
    for nombre in sys.argv[3:]:
        n = c.execute("UPDATE sucursales SET usa_niveles_precio = 1 WHERE nombre = ?", (nombre,)).rowcount
        print(("  %s usa niveles de precio" % nombre) if n else ("  ⚠ no existe la sucursal %s" % nombre))
    c.commit()

print()
for r in c.execute("select coalesce(sucursal,'(todas)'), count(*) from clientes group by 1"):
    print("  clientes en %-12s %d" % r)
