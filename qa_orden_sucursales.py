"""Agrega sucursales.orden y baja al final las sucursales que se indiquen.

Sin orden explícito todas valen 0 y se listan alfabéticamente, como hasta ahora.
Idempotente.

    python3 qa_orden_sucursales.py inventario.db "El Zar"
"""
import sqlite3
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
al_final = sys.argv[2:]

c = sqlite3.connect(ruta)
if "orden" in [r[1] for r in c.execute("pragma table_info(sucursales)")]:
    print("La columna orden ya existía.")
else:
    c.execute("ALTER TABLE sucursales ADD COLUMN orden INTEGER DEFAULT 0")
    c.execute("UPDATE sucursales SET orden = 0")
    print("Columna orden agregada, todas en 0 (alfabético).")

for nombre in al_final:
    n = c.execute("UPDATE sucursales SET orden = 1 WHERE nombre = ?", (nombre,)).rowcount
    print(("  %s pasa al final" % nombre) if n else ("  ⚠ no existe la sucursal %s" % nombre))

c.commit()
print()
for r in c.execute("select nombre, orden from sucursales order by orden, nombre"):
    print("  %-18s orden %s" % r)
