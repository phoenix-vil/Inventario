#!/usr/bin/env python3
"""
Agrega marcas a los productos existentes para poder filtrarlos.
Uso: python3 actualizar_marcas.py [ruta_db]
"""
import sqlite3, sys, re

DB = sys.argv[1] if len(sys.argv) > 1 else "inventario.db"

# Mapeo nombre/fragmento → marca
MARCAS_POR_PATRON = [
    # Bebidas
    (r"refresco cola",       "Coca-Cola"),
    (r"agua natural",        "Bonafont"),
    (r"agua mineral",        "Peñafiel"),
    (r"jugo de naranja",     "Jumex"),
    (r"jugo de manzana",     "Del Valle"),
    (r"bebida energética",   "Monster"),
    (r"té helado",           "Nestea"),
    (r"leche entera",        "Lala"),
    (r"leche deslactosada",  "Alpura"),
    (r"yogur bebible",       "Yakult"),
    (r"café embotellado",    "Nescafé"),
    # Dulces
    (r"chicles menta",       "Trident"),
    (r"chicles canela",      "Cinnamon"),
    (r"paleta de caramelo",  "Dulces Vero"),
    (r"chocolate con leche", "Hershey's"),
    (r"chocolate amargo",    "Abuelita"),
    (r"chocolate blanco",    "Milky Way"),
    (r"gomitas",             "Ricolino"),
    (r"caramelos",           "Ricolino"),
    (r"mazapán",             "De La Rosa"),
    (r"paleta de chile",     "Dulces Vero"),
    (r"malvaviscos",         "Ricolino"),
    (r"tableta",             "Hershey's"),
    (r"dulce de tamarindo",  "Pelon Pelo Rico"),
    # Botanas
    (r"papas fritas",        "Sabritas"),
    (r"cacahuates",          "Mafer"),
    (r"churritos",           "Barcel"),
    (r"palomitas",           "Pop Secret"),
    (r"frituras de harina",  "Barcel"),
    (r"totopos",             "Tía Rosa"),
    (r"semillas de girasol", "Barcel"),
    (r"chicharrones",        "Sabritas"),
    (r"galletas saladas",    "Gamesa"),
    (r"mix de frutos",       "Mafer"),
    # Abarrotes
    (r"arroz",               "La Costeña"),
    (r"frijol",              "La Costeña"),
    (r"azúcar",              "Zulka"),
    (r"sal de mesa",         "La Fina"),
    (r"aceite vegetal",      "Capullo"),
    (r"harina de trigo",     "Selecta"),
    (r"pasta espagueti",     "La Moderna"),
    (r"sopa de letras",      "Maruchan"),
    (r"atún en lata",        "Dolores"),
    (r"sardinas",            "El Mexicano"),
    (r"lentejas",            "La Costeña"),
    (r"café soluble",        "Nescafé"),
    (r"consomé de pollo",    "Knorr"),
    (r"mayonesa",            "McCormick"),
    (r"catsup",              "Heinz"),
    (r"mostaza",             "McCormick"),
    # Limpieza
    (r"jabón de barra",      "Dove"),
    (r"detergente",          "Ariel"),
    (r"cloro",               "Cloralex"),
    (r"limpiador multiusos", "Fabuloso"),
    (r"jabón para trastes",  "Axion"),
    (r"suavizante",          "Suavitel"),
    (r"bolsas de basura",    "Hefty"),
    (r"papel higiénico",     "Kleenex"),
    (r"servilletas",         "Kleenex"),
    (r"toallas de papel",    "Scottex"),
    # Higiene
    (r"pasta dental",        "Colgate"),
    (r"cepillo de dientes",  "Oral-B"),
    (r"shampoo",             "Pantene"),
    (r"jabón de tocador",    "Dove"),
    (r"desodorante",         "Rexona"),
    (r"rastrillo",           "Gillette"),
    (r"toallas femeninas",   "Kotex"),
    (r"papel facial",        "Kleenex"),
    (r"algodón",             "Johnson's"),
    (r"cotonetes",           "Johnson's"),
    # Lácteos y refrigerados
    (r"queso panela",        "Lala"),
    (r"queso oaxaca",        "Chilchota"),
    (r"crema ácida",         "Lala"),
    (r"mantequilla",         "Alpura"),
    (r"huevo",               "Bachoco"),
    (r"jamón de pavo",       "FUD"),
    (r"salchichas",          "FUD"),
    (r"tortillas de harina", "Tía Rosa"),
    (r"yogur natural",       "Yoplait"),
    (r"gelatina preparada",  "Jell-O"),
    # Panadería
    (r"pan de caja blanco",  "Bimbo"),
    (r"pan integral",        "Bimbo"),
    (r"pan dulce",           "Marinela"),
    (r"donas",               "Marinela"),
    (r"pan molido",          "Bimbo"),
    (r"tostadas",            "Charras"),
    (r"galletas marías",     "Gamesa"),
    (r"galletas de chocolate","Oreo"),
    (r"barritas de fresa",   "Marinela"),
    (r"pastelito",           "Marinela"),
    # Papelería
    (r"cuaderno",            "Scribe"),
    (r"bolígrafo",           "Bic"),
    (r"lápiz",               "Faber-Castell"),
    (r"cinta adhesiva",      "Scotch"),
    (r"pegamento",           "Resistol"),
    (r"tijeras",             "Maped"),
]

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='productos'")
    if not cur.fetchone():
        print(f"ERROR: tabla 'productos' no encontrada en {DB}")
        sys.exit(1)

    cur.execute("SELECT id, nombre FROM productos WHERE marca IS NULL OR marca = ''")
    productos = cur.fetchall()
    if not productos:
        print("Todos los productos ya tienen marca asignada.")
        conn.close(); return

    actualizados = 0
    sin_marca = 0
    for pid, nombre in productos:
        nombre_lower = nombre.lower()
        marca = None
        for patron, m in MARCAS_POR_PATRON:
            if re.search(patron, nombre_lower):
                marca = m
                break
        if marca:
            cur.execute("UPDATE productos SET marca=? WHERE id=?", (marca, pid))
            actualizados += 1
        else:
            sin_marca += 1

    conn.commit()
    conn.close()
    print(f"✓ {actualizados} productos actualizados con marca.")
    if sin_marca:
        print(f"  {sin_marca} productos sin marca reconocida (puedes asignarlas manualmente).")

if __name__ == "__main__":
    main()
