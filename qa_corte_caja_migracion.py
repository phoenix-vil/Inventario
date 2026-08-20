"""Crea la tabla cortes_caja en una base existente.

create_all() de init_db() ya la crea sola al arrancar, así que este script solo
hace falta si se quiere preparar la base antes de desplegar el código nuevo, o
para comprobar que quedó bien. Es idempotente.

    python3 qa_corte_caja_migracion.py [ruta_a_inventario.db]
"""
import sqlite3
import sys

ruta = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"
c = sqlite3.connect(ruta)

existe = c.execute(
    "select name from sqlite_master where type='table' and name='cortes_caja'"
).fetchone()

if existe:
    print("La tabla cortes_caja ya existe, no se toca nada.")
else:
    c.execute("""
        CREATE TABLE cortes_caja (
            id INTEGER PRIMARY KEY,
            sucursal VARCHAR NOT NULL,
            operador VARCHAR,
            desde DATETIME,
            creado_en DATETIME,
            saldo_inicial FLOAT,
            ventas_efectivo FLOAT,
            abonos_efectivo FLOAT,
            gastos_efectivo FLOAT,
            esperado FLOAT,
            contado FLOAT,
            diferencia FLOAT,
            retirado FLOAT,
            nota VARCHAR
        )
    """)
    c.execute("CREATE INDEX ix_cortes_caja_sucursal ON cortes_caja (sucursal)")
    c.execute("CREATE INDEX ix_cortes_caja_creado_en ON cortes_caja (creado_en)")
    c.commit()
    print("Tabla cortes_caja creada.")

print("Columnas:", [r[1] for r in c.execute("pragma table_info(cortes_caja)")])
print("Cortes registrados:", c.execute("select count(*) from cortes_caja").fetchone()[0])
