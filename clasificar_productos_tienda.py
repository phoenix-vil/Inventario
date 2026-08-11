"""
Clasificación automática de productos por tienda (submarca), Fase 1.

Script de una sola vez — NO es parte de la app, no se vuelve a ejecutar tras
aplicarse (ver CLAUDE.md, sección "Los scripts sueltos"). A diferencia de los
qa_*.py (que parchan código), este toca datos: asigna Producto.tienda según
el fabricante (categoria/marca), usando el mapeo revisado y aprobado por el
usuario. Todo lo no incluido en el mapeo queda tienda=NULL (visible en las
5 tiendas), para que cada gerente lo revise en /tiendas-clasificar.

Uso:
  python3 clasificar_productos_tienda.py           # dry-run: solo imprime el resumen
  python3 clasificar_productos_tienda.py --apply    # aplica los UPDATE de verdad
"""
import sqlite3
import sys

DB = "inventario.db"

MAPA = {
    "Only Reef": [
        "Aqua Forest", "Tropic Marine", "Red Sea", "Brightwell aquatics",
        "Two Little Fishies", "Coral Box", "ATI", "Bulk Reef Suply", "Triton",
        "Fauna Marin", "Salifert", "Polyp Lab", "Easy Reefs", "Lab Reef",
        "Instant ocean", "Reef Octopus", "Neptune System", "Marine Pure",
        "Nyos", "Innovative Marine", "Blue Life", "Ruby Reef", "Aqua Vitro",
        "Ecotech", "Tunze", "Benereefs", "DD Aquarium solution",
        "Ocean nutrition", "American Marine Inc,", "Kamoer", "CaribSea",
        "Reefers", "Coral Rx", "JBJ", "Ocean free", "Hydros", "RedStarfish",
        "Blau", "Premium Aquatics",
    ],
    "Only Reptile": [
        "ZooMed", "Repashy", "Pangea", "Exoterra", "Arcadia", "Mazuri",
        "Terraria", "Fluker's", "Nomoy Pet Reptile", "ReptilTerra",
        "Probugs", "MistKing", "Sistema de Lluvia", "Exotic's",
        "Only Reptile", "ZooMania",
    ],
    "Only Garden": [
        # Only Garden = todo lo de acuarios de agua dulce (confirmado con el usuario)
        "ADA", "UNS", "Dennerle", "Culivos", "FitoMix", "Planta", "Aquascape",
        "Oase", "Fluval", "Eheim", "Tetra", "Sera", "JBL", "Boyu", "Aquario",
        "Ista", "Qanvee", "eSHa", "ViaAqua", "Tender Living Care",
    ],
    "El Zar del LED": [
        "Chihiros", "Aqua Illumination", "Maxspect", "Orphek", "Twinstar",
        "Week Aqua", "Zar del LED",
    ],
    "Only Pets": [
        "Petmmal", "The Other Paws",
    ],
    # Nota: "Simón Blanco" queda deliberadamente SIN mapear — el usuario
    # confirmó que esa marca vende tanto peceras (Only Garden) como
    # terrarios (Only Reptile) y no hay forma de distinguir por nombre.
}


def main():
    aplicar = "--apply" in sys.argv
    con = sqlite3.connect(DB)
    cur = con.cursor()

    total = cur.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    sin_antes = cur.execute("SELECT COUNT(*) FROM productos WHERE tienda IS NULL").fetchone()[0]

    print(f"Total productos: {total}")
    print(f"Sin clasificar antes: {sin_antes}\n")

    resumen = {}
    for tienda, marcas in MAPA.items():
        placeholders = ",".join("?" for _ in marcas)
        cur.execute(
            f"SELECT COUNT(*) FROM productos WHERE tienda IS NULL AND "
            f"(categoria IN ({placeholders}) OR marca IN ({placeholders}))",
            marcas + marcas,
        )
        n = cur.fetchone()[0]
        resumen[tienda] = n
        print(f"{tienda:20s} -> {n:5d} productos ({', '.join(marcas)})")

        if aplicar:
            cur.execute(
                f"UPDATE productos SET tienda = ? WHERE tienda IS NULL AND "
                f"(categoria IN ({placeholders}) OR marca IN ({placeholders}))",
                [tienda] + marcas + marcas,
            )

    if aplicar:
        con.commit()
        sin_despues = cur.execute("SELECT COUNT(*) FROM productos WHERE tienda IS NULL").fetchone()[0]
        print(f"\nAPLICADO. Sin clasificar después: {sin_despues} "
              f"(quedan visibles en las 5 tiendas hasta que se revisen)")
    else:
        total_clasificados = sum(resumen.values())
        print(f"\nDRY-RUN (nada se guardó). Se clasificarían {total_clasificados} productos.")
        print(f"Quedarían sin clasificar: {sin_antes - total_clasificados}")
        print("Corre con --apply para aplicar de verdad.")

    con.close()


if __name__ == "__main__":
    main()
