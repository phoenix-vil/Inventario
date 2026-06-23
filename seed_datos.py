#!/usr/bin/env python3
"""Genera 100 productos de prueba con códigos EAN-13 válidos.
Uso: python3 seed_datos.py [ruta_db]
Por defecto usa ./inventario.db
"""
import sqlite3
import random
import sys
from datetime import datetime

DB = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"

CATALOGO = {
    "Bebidas": [
        ("Refresco cola 600ml", 20, 12), ("Refresco cola 2L", 38, 26),
        ("Agua natural 600ml", 12, 6), ("Agua natural 1.5L", 18, 10),
        ("Jugo de naranja 1L", 32, 20), ("Jugo de manzana 500ml", 22, 13),
        ("Bebida energética 473ml", 35, 24), ("Té helado limón 600ml", 19, 11),
        ("Agua mineral 600ml", 15, 8), ("Refresco naranja 600ml", 19, 11),
        ("Refresco toronja 600ml", 19, 11), ("Leche entera 1L", 27, 19),
        ("Leche deslactosada 1L", 30, 22), ("Yogur bebible fresa 250ml", 16, 9),
        ("Café embotellado 280ml", 28, 18),
    ],
    "Dulces": [
        ("Chicles menta", 12, 6), ("Paleta de caramelo", 5, 2),
        ("Chocolate con leche 40g", 18, 11), ("Chocolate amargo 40g", 22, 14),
        ("Gomitas de frutas 80g", 15, 8), ("Caramelos surtidos 100g", 20, 12),
        ("Mazapán", 8, 4), ("Tableta de chocolate blanco", 24, 15),
        ("Dulce de tamarindo", 10, 5), ("Paleta de chile", 7, 3),
        ("Malvaviscos 120g", 18, 10), ("Chicles canela", 12, 6),
    ],
    "Botanas": [
        ("Papas fritas 45g", 18, 11), ("Papas fritas 170g", 42, 28),
        ("Cacahuates salados 100g", 16, 9), ("Cacahuates enchilados 100g", 17, 10),
        ("Churritos de maíz 60g", 12, 6), ("Palomitas mantequilla 40g", 14, 7),
        ("Frituras de harina 50g", 10, 5), ("Totopos 200g", 28, 17),
        ("Semillas de girasol 60g", 13, 7), ("Chicharrones de cerdo 80g", 35, 22),
        ("Galletas saladas 137g", 19, 12), ("Mix de frutos secos 90g", 38, 25),
    ],
    "Abarrotes": [
        ("Arroz 1kg", 32, 22), ("Frijol negro 1kg", 40, 28),
        ("Azúcar 1kg", 30, 21), ("Sal de mesa 1kg", 14, 8),
        ("Aceite vegetal 1L", 48, 36), ("Harina de trigo 1kg", 24, 16),
        ("Pasta espagueti 200g", 12, 7), ("Sopa de letras 200g", 12, 7),
        ("Atún en lata 140g", 22, 15), ("Sardinas en lata 425g", 35, 24),
        ("Lentejas 500g", 26, 17), ("Café soluble 100g", 58, 42),
        ("Consomé de pollo 8 cubos", 18, 11), ("Mayonesa 390g", 42, 30),
        ("Catsup 397g", 30, 20), ("Mostaza 220g", 24, 15),
    ],
    "Limpieza": [
        ("Jabón de barra", 16, 9), ("Detergente en polvo 1kg", 38, 26),
        ("Cloro 1L", 22, 14), ("Limpiador multiusos 1L", 32, 21),
        ("Jabón para trastes 750ml", 35, 23), ("Suavizante de telas 850ml", 30, 19),
        ("Escoba", 55, 35), ("Fibra para trastes", 8, 4),
        ("Bolsas de basura 10pz", 25, 15), ("Papel higiénico 4 rollos", 38, 26),
        ("Servilletas 250pz", 28, 18), ("Toallas de papel 1 rollo", 26, 16),
    ],
    "Higiene": [
        ("Pasta dental 75ml", 28, 18), ("Cepillo de dientes", 22, 13),
        ("Shampoo 400ml", 52, 36), ("Jabón de tocador", 18, 10),
        ("Desodorante en barra", 42, 28), ("Rastrillo desechable 2pz", 25, 15),
        ("Toallas femeninas 10pz", 32, 21), ("Papel facial 90pz", 30, 19),
        ("Algodón 50g", 16, 9), ("Cotonetes 100pz", 18, 11),
    ],
    "Lácteos y refrigerados": [
        ("Queso panela 400g", 58, 42), ("Queso Oaxaca 400g", 64, 47),
        ("Crema ácida 450ml", 36, 25), ("Mantequilla 90g", 24, 16),
        ("Huevo 12pz", 42, 32), ("Jamón de pavo 250g", 45, 32),
        ("Salchichas 500g", 48, 34), ("Tortillas de harina 10pz", 26, 17),
        ("Yogur natural 1kg", 38, 26), ("Gelatina preparada 125g", 8, 4),
    ],
    "Panadería": [
        ("Pan de caja blanco 680g", 42, 30), ("Pan integral 680g", 48, 35),
        ("Pan dulce pieza", 9, 4), ("Donas 6pz", 35, 22),
        ("Pan molido 210g", 20, 12), ("Tostadas 360g", 24, 15),
        ("Galletas marías 170g", 15, 9), ("Galletas de chocolate 100g", 17, 10),
        ("Barritas de fresa 8pz", 32, 20), ("Pastelito de chocolate", 14, 8),
    ],
    "Papelería": [
        ("Cuaderno profesional 100h", 28, 18), ("Bolígrafo negro", 8, 4),
        ("Lápiz HB", 5, 2), ("Cinta adhesiva 12mm", 14, 8),
        ("Pegamento en barra 8g", 16, 9), ("Tijeras escolares", 22, 13),
    ],
}


def ean13_con_verificador(base12: str) -> str:
    """Calcula el dígito verificador EAN-13 para 12 dígitos base."""
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return base12 + str((10 - suma % 10) % 10)


def generar_ean13(usados: set) -> str:
    while True:
        # Prefijo 750 = México
        base = "750" + "".join(random.choices("0123456789", k=9))
        codigo = ean13_con_verificador(base)
        if codigo not in usados:
            usados.add(codigo)
            return codigo


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Verificar tabla
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='productos'")
    if not cur.fetchone():
        print(f"ERROR: la tabla 'productos' no existe en {DB}")
        print("Asegúrate de correr este script en la carpeta del proyecto, o pasa la ruta correcta:")
        print("  python3 seed_datos.py /ruta/a/inventario.db")
        sys.exit(1)

    # Códigos ya existentes para no duplicar
    cur.execute("SELECT codigo_barras FROM productos WHERE codigo_barras IS NOT NULL")
    usados = {r[0] for r in cur.fetchall()}

    items = []
    for categoria, productos in CATALOGO.items():
        for nombre, precio, costo in productos:
            items.append((categoria, nombre, precio, costo))

    random.shuffle(items)
    items = items[:100]

    ahora = datetime.utcnow().isoformat(sep=" ")
    insertados = 0
    for categoria, nombre, precio, costo in items:
        codigo = generar_ean13(usados)
        stock = random.randint(0, 60)
        stock_minimo = random.choice([3, 5, 8, 10])
        # ~15% de productos con descuento de temporada
        descuento = random.choice([0]*17 + [10, 15, 20])
        try:
            cur.execute(
                """INSERT INTO productos
                   (nombre, categoria, codigo_barras, precio_venta, precio_costo,
                    stock, stock_minimo, unidad, descuento_pct, creado_en, actualizado_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'pieza', ?, ?, ?)""",
                (nombre, categoria, codigo, precio, costo, stock, stock_minimo, descuento, ahora, ahora),
            )
            insertados += 1
        except sqlite3.IntegrityError:
            pass  # nombre/código duplicado, saltar

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM productos")
    total = cur.fetchone()[0]
    conn.close()
    print(f"✓ {insertados} productos de prueba insertados. Total en BD: {total}")
    print("Los códigos EAN-13 generados son válidos (dígito verificador correcto).")


if __name__ == "__main__":
    main()
