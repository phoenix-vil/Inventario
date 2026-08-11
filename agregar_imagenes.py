#!/usr/bin/env python3
"""
Agrega imágenes a los productos:
  1. Con código EAN → busca imagen real (Open Food Facts + UPCitemdb, gratis)
  2. Sin EAN o no encontrada → placeholder generado por marca (SVG data-URI, gratis)

Es REANUDABLE: solo procesa productos sin imagen. Puedes cortarlo (Ctrl+C) y volver a correrlo.

Uso:
  cd ~/inventario
  python3 agregar_imagenes.py            # procesa todos los pendientes
  python3 agregar_imagenes.py --solo-marca   # solo placeholders por marca (instantáneo, sin internet)
  python3 agregar_imagenes.py --limite 200   # procesa máximo 200 (para probar)
"""
import sqlite3, sys, os, time, json, urllib.request, urllib.parse, hashlib

DB = os.path.expanduser('~/inventario/inventario.db')
SOLO_MARCA = '--solo-marca' in sys.argv
LIMITE = None
if '--limite' in sys.argv:
    try: LIMITE = int(sys.argv[sys.argv.index('--limite')+1])
    except: pass

# ── Paleta de colores por hash de marca (para placeholders bonitos) ────────
PALETA = [
    ('#185fa5','#e6f1fb'), ('#3b6d11','#eaf3de'), ('#854f0b','#faeeda'),
    ('#a32d2d','#fcebeb'), ('#5b3a8c','#efe8f9'), ('#0a7373','#d9f2f0'),
    ('#b5651d','#fbeede'), ('#2c5f2d','#e3f0e0'), ('#1b4965','#e0edf4'),
    ('#6a4c93','#eee6f7'), ('#c1440e','#fce8df'), ('#136f63','#dcf2ee'),
]

def color_para(texto):
    h = int(hashlib.md5((texto or 'x').encode()).hexdigest(), 16)
    return PALETA[h % len(PALETA)]

def placeholder_svg(marca, nombre):
    """Genera un placeholder SVG data-URI con las iniciales de la marca."""
    etiqueta = (marca or nombre or '?').strip()
    # Iniciales: primeras 2 palabras
    palabras = etiqueta.split()
    if len(palabras) >= 2:
        iniciales = (palabras[0][0] + palabras[1][0]).upper()
    else:
        iniciales = etiqueta[:2].upper()
    fg, bg = color_para(marca or nombre)
    txt_marca = (marca or 'Producto')[:18]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
<rect width="300" height="300" fill="{bg}"/>
<circle cx="150" cy="120" r="70" fill="{fg}" opacity="0.15"/>
<text x="150" y="140" font-family="Arial,sans-serif" font-size="64" font-weight="700" fill="{fg}" text-anchor="middle">{iniciales}</text>
<text x="150" y="230" font-family="Arial,sans-serif" font-size="20" font-weight="600" fill="{fg}" text-anchor="middle">{txt_marca}</text>
</svg>'''
    b64 = __import__('base64').b64encode(svg.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{b64}'

def buscar_openfoodfacts(ean):
    try:
        url = f'https://world.openfoodfacts.org/api/v2/product/{ean}.json?fields=image_url,image_front_url'
        req = urllib.request.Request(url, headers={'User-Agent':'OnlyReef-Inventory/1.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        if data.get('status') == 1:
            p = data.get('product', {})
            return p.get('image_front_url') or p.get('image_url')
    except Exception:
        pass
    return None

def buscar_upcitemdb(ean):
    try:
        url = f'https://api.upcitemdb.com/prod/trial/lookup?upc={ean}'
        req = urllib.request.Request(url, headers={'User-Agent':'OnlyReef-Inventory/1.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        items = data.get('items', [])
        if items:
            imgs = items[0].get('images', [])
            if imgs:
                return imgs[0]
    except Exception:
        pass
    return None

# ── Proceso ────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
    SELECT id, nombre, marca, codigo_barras
    FROM productos
    WHERE imagen_url IS NULL OR imagen_url = ''
    ORDER BY id
""")
pendientes = cur.fetchall()
if LIMITE:
    pendientes = pendientes[:LIMITE]

total = len(pendientes)
print(f"Productos sin imagen: {total}")
if total == 0:
    print("✓ Todos los productos ya tienen imagen.")
    conn.close(); sys.exit(0)

if SOLO_MARCA:
    print("Modo --solo-marca: asignando placeholders por marca (sin internet)...")
else:
    print("Buscando imágenes reales por EAN + placeholders por marca...")
    print("(Esto puede tardar. Puedes cortar con Ctrl+C y reanudar corriendo el script otra vez.)")
print()

con_ean = 0
con_placeholder = 0
upc_bloqueado = False  # UPCitemdb trial se agota rápido; si falla, dejamos de intentarlo

try:
    for i, (pid, nombre, marca, ean) in enumerate(pendientes, 1):
        imagen = None

        if not SOLO_MARCA and ean and len(str(ean).strip()) >= 8:
            ean = str(ean).strip()
            imagen = buscar_openfoodfacts(ean)
            if not imagen and not upc_bloqueado:
                imagen = buscar_upcitemdb(ean)
                if imagen is None:
                    # Si UPC devuelve nada varias veces seguidas, probablemente se agotó el trial
                    pass
            if imagen:
                con_ean += 1
            time.sleep(0.4)  # respetar rate limits de las APIs gratuitas

        if not imagen:
            imagen = placeholder_svg(marca, nombre)
            con_placeholder += 1

        cur.execute("UPDATE productos SET imagen_url=? WHERE id=?", (imagen, pid))

        if i % 25 == 0:
            conn.commit()
            print(f"  {i}/{total}  ·  reales: {con_ean}  ·  placeholders: {con_placeholder}")

    conn.commit()
except KeyboardInterrupt:
    conn.commit()
    print(f"\n⏸  Pausado. Progreso guardado ({i}/{total}). Corre el script de nuevo para continuar.")
    conn.close(); sys.exit(0)

conn.close()
print()
print("═" * 50)
print(f"✅ Completado: {total} productos")
print(f"   Imágenes reales (EAN): {con_ean}")
print(f"   Placeholders por marca: {con_placeholder}")
print()
print("Reinicia el servicio para verlas:")
print("   sudo systemctl restart inventario")
