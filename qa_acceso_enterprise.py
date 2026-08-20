"""Agrega usuarios.acceso_enterprise y concede el permiso a quien se indique.

create_all() no añade columnas a tablas existentes, así que esta es obligatoria
antes de desplegar el código nuevo: sin ella el login falla al leer la columna.
Es idempotente.

    python3 qa_acceso_enterprise.py inventario.db "Daniel Mondragon" Phoenix
"""
import sqlite3
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
autorizados = sys.argv[2:]

c = sqlite3.connect(ruta)

columnas = [r[1] for r in c.execute("pragma table_info(usuarios)")]
if "acceso_enterprise" in columnas:
    print("La columna acceso_enterprise ya existía.")
else:
    c.execute("ALTER TABLE usuarios ADD COLUMN acceso_enterprise BOOLEAN DEFAULT 0")
    c.execute("UPDATE usuarios SET acceso_enterprise = 0")
    print("Columna acceso_enterprise agregada, todos en 0.")

for nombre in autorizados:
    n = c.execute("UPDATE usuarios SET acceso_enterprise = 1 WHERE usuario = ?", (nombre,)).rowcount
    print(("  concedido a %s" % nombre) if n else ("  ⚠ no existe el usuario %s" % nombre))

c.commit()
print()
for r in c.execute("select usuario, rol, acceso_enterprise from usuarios order by usuario"):
    print("  %-20s %-9s acceso Only Enterprises: %s" % (r[0], r[1], "sí" if r[2] else "no"))
