"""Agrega sucursales.usuarios_permitidos.

create_all() no añade columnas a tablas existentes, así que hay que correrlo
antes de arrancar el código nuevo. Idempotente.

    python3 qa_usuarios_permitidos.py inventario.db
"""
import sqlite3
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
c = sqlite3.connect(ruta)

if "usuarios_permitidos" in [r[1] for r in c.execute("pragma table_info(sucursales)")]:
    print("La columna usuarios_permitidos ya existía.")
else:
    c.execute("ALTER TABLE sucursales ADD COLUMN usuarios_permitidos TEXT")
    c.commit()
    print("Columna usuarios_permitidos agregada (vacía = cualquiera puede entrar).")

for r in c.execute("select nombre, coalesce(tiendas,''), coalesce(usuarios_permitidos,'') from sucursales order by nombre"):
    print("  %-18s tiendas: %-28s acceso: %s" % (r[0], r[1] or '—', r[2] or 'cualquiera'))
