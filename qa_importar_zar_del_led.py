#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Importa el catálogo de "El Zar del LED" desde el Excel que mandó el
usuario y crea la sucursal para venderlo.

Fuente: BD_Zar_del_Led.xls (formato antiguo BIFF, exportado de SICAR, el POS
anterior de ese negocio). Columnas: CLAVE, DESCRIPCION, PRECIO COMPRA,
PRECIO 1, PRECIO 2, MAYOREO 2, PRECIO 3, MAYOREO 3, PRECIO 4, MAYOREO 4,
EXIST., DEPARTAMENTO, CATEGORIA.

Mapeo a productos (versión final, tras dos ajustes pedidos por el usuario):
  CLAVE          -> clave (columna dedicada: es la clave interna con la que
                    ya estaban acostumbrados a buscar en SICAR, no un EAN)
  DESCRIPCION    -> nombre
  PRECIO COMPRA  -> precio_costo
  PRECIO 1       -> precio_venta (precio de menudeo)
  PRECIO 2       -> precio_1
  PRECIO 3       -> precio_2
  PRECIO 4       -> precio_3
  EXIST.         -> se importa pero luego se puso en 0 para los 111 (el
                    usuario pidió arrancar el conteo desde cero, sin
                    arrastrar las existencias -muchas negativas- del sistema
                    anterior)
  CATEGORIA      -> categoria (DEPARTAMENTO no tiene campo equivalente y se
                    descarta; 3 filas traen "SIN DEFINIR"/"El Zar del Led"
                    cruzados por un error de exportación -> "VARIOS")
  codigo_barras  -> vacío (el usuario pidió dejarlo así; el código real de
                    barras es un concepto aparte de la clave interna)
  marca          -> vacío (sin dato en el archivo origen)
  tienda         -> "El Zar del LED" fijo (ya existe como Tienda)

Los "MAYOREO 2/3/4" (cantidad mínima para cada precio de mayoreo) NO tienen
campo equivalente: aquí el precio de mayoreo depende del nivel del cliente
(1/2/3), no de cuánto compre en el momento. Solo 3 de 113 productos usaban
de verdad ese umbral (>0), así que el impacto real es mínimo.

Se excluyen del catálogo "ANTICIPO LAMPARA LED" y "LIQUIDACION DE LAMPARA
LED" (precio y existencia en $0 en el archivo origen): un producto de
catálogo no puede cobrar un monto libre, solo tiene un precio fijo que a lo
más se puede rebajar con descuento. En su lugar, /pagos tiene dos atajos
("💰 Anticipo" / "🧾 Liquidación") que abren "+ Personalizado" con el nombre
ya puesto, visibles solo para la sucursal de El Zar del LED.

Requiere que la columna `clave` ya exista en productos (ver qa_agregar_clave
o el ALTER TABLE equivalente) y que main.py tenga el campo `clave` en
ProductoBase/ProductoOut -de lo contrario el insert de más abajo funciona
igual, pero /api/productos no lo va a devolver hasta actualizar el código-.

Uso: cd ~/inventario-qa && python3 qa_importar_zar_del_led.py
Idempotente: si ya hay productos con tienda='El Zar del LED', no hace nada.
"""
import os
import sqlite3
from datetime import datetime, timezone

try:
    import xlrd
except ImportError:
    raise SystemExit("Falta xlrd: pip3 install --user --break-system-packages xlrd")

XLS = os.path.expanduser(
    "/home/phoenix/.claude/uploads/946d7416-c6bb-552c-b945-4a952c02b76d/ed6d8418-BD_Zar_del_Led.xls"
)
DB = os.path.expanduser("~/inventario-qa/inventario.db")
TIENDA = "El Zar del LED"
SUCURSAL = "Zar del Led"

FILAS_EXCLUIDAS = {"ANTICIPO LAMPARA LED", "LIQUIDACION DE LAMPARA LED"}


def f(valor, default=0.0):
    """Las celdas vienen mezcladas: a veces texto ('8.000000'), a veces
    número (8.0), según cómo se haya capturado la celda en Excel."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def main():
    wb = xlrd.open_workbook(XLS)
    sh = wb.sheet_by_name("Sheet0")

    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM productos WHERE tienda = ?", (TIENDA,))
    if cur.fetchone()[0] > 0:
        print(f"Ya hay productos con tienda='{TIENDA}'. No se importa de nuevo.")
        con.close()
        return

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    filas_insertadas = 0
    omitidas = []

    for r in range(1, sh.nrows):
        clave = str(sh.cell_value(r, 0)).strip()
        nombre = str(sh.cell_value(r, 1)).strip()
        if nombre in FILAS_EXCLUIDAS or clave in FILAS_EXCLUIDAS:
            omitidas.append(nombre)
            continue

        precio_costo = f(sh.cell_value(r, 2))
        precio_venta = f(sh.cell_value(r, 3)) or 1  # 0 no pasa la validación (gt=0); "reguladores" es el único caso
        precio_1 = f(sh.cell_value(r, 4))
        precio_2 = f(sh.cell_value(r, 6))
        precio_3 = f(sh.cell_value(r, 8))
        departamento = str(sh.cell_value(r, 11)).strip()
        categoria = str(sh.cell_value(r, 12)).strip()

        # 3 filas traen la categoría real perdida (el nombre de la tienda se
        # coló en la columna CATEGORIA por un error del sistema anterior).
        if departamento == "SIN DEFINIR" or categoria == "El Zar del Led":
            categoria = "VARIOS"

        cur.execute(
            """INSERT INTO productos
               (nombre, categoria, precio_venta, precio_costo, stock, stock_minimo,
                unidad, creado_en, actualizado_en, codigo_barras, clave, descuento_pct,
                vendido_por_peso, marca, tienda, precio_1, precio_2, precio_3)
               VALUES (?, ?, ?, ?, 0, 0, 'pieza', ?, ?, NULL, ?, 0, 0, NULL, ?, ?, ?, ?)""",
            (nombre, categoria or "VARIOS", precio_venta, precio_costo,
             ahora, ahora, clave or None, TIENDA, precio_1, precio_2, precio_3),
        )
        filas_insertadas += 1

    # La sucursal que vende esta tienda: usa_niveles_precio=1 porque el
    # catálogo trae 3 precios de mayoreo (precio_1/2/3) además del de menudeo;
    # catalogo_exclusivo=1 porque es la única sucursal que vende esta tienda,
    # no debe heredar el catálogo general de las demás (Only Reef/Garden/...).
    cur.execute("SELECT id FROM sucursales WHERE nombre = ?", (SUCURSAL,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO sucursales (nombre, tiendas, usuarios_permitidos, orden, "
            "usa_niveles_precio, catalogo_exclusivo, creado_en) "
            "VALUES (?, ?, NULL, 0, 1, 1, ?)",
            (SUCURSAL, TIENDA, ahora),
        )
        print(f"Sucursal '{SUCURSAL}' creada (tiendas='{TIENDA}', usa_niveles_precio=1, catalogo_exclusivo=1).")
    else:
        print(f"Sucursal '{SUCURSAL}' ya existía, no se toca.")

    con.commit()
    con.close()

    print(f"Productos importados: {filas_insertadas}")
    print(f"Filas omitidas (no son producto de catálogo): {omitidas}")
    print("Recuerda: el stock se dejó en 0 para todos a propósito (recuento desde cero).")


if __name__ == "__main__":
    main()
