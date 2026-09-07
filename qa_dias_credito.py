#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Migración de la base para el plazo de crédito por cliente.

Agrega clientes.dias_credito, que usa el aviso de cobranza del inicio de
sesión. init_db() no agrega columnas a tablas que ya existen, así que hay que
correr esto. Es idempotente.

Uso: cd ~/inventario-qa && python3 qa_dias_credito.py [ruta_bd]
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
agregar("clientes", "dias_credito", "INTEGER")
c.commit()
con_plazo = c.execute("SELECT COUNT(*) FROM clientes WHERE dias_credito IS NOT NULL").fetchone()[0]
total = c.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
print("Clientes con plazo de crédito: %d de %d" % (con_plazo, total))
c.close()
