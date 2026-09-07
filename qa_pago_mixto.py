#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Migración de la base para el cobro con dos formas de pago.

init_db() solo crea tablas nuevas, nunca agrega columnas a las que ya
existen, así que las dos columnas nuevas de `ventas` hay que añadirlas a
mano. Es idempotente: si ya están, no hace nada.

Uso: cd ~/inventario-qa && python3 qa_pago_mixto.py [ruta_bd]
"""
import sqlite3
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
c = sqlite3.connect(ruta)


def agregar(tabla, columna, tipo):
    if columna in [r[1] for r in c.execute("pragma table_info(%s)" % tabla)]:
        print("  ya existía: %s.%s" % (tabla, columna))
        return False
    c.execute("ALTER TABLE %s ADD COLUMN %s %s" % (tabla, columna, tipo))
    print("  agregada:   %s.%s" % (tabla, columna))
    return True


print("Base: %s" % ruta)
agregar("ventas", "metodo_pago_2", "VARCHAR")
agregar("ventas", "monto_2", "FLOAT")
c.commit()

mixtas = c.execute("SELECT COUNT(*) FROM ventas WHERE metodo_pago_2 IS NOT NULL").fetchone()[0]
print("Ventas con dos formas de pago: %d" % mixtas)
c.close()
