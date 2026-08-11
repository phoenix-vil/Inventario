#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca imagenes REALES de producto usando la API de Serper.dev (Google Images),
solo para los productos que actualmente tienen un placeholder (icono generico
de marca) en vez de una foto real. No toca los que ya tienen imagen de
Open Food Facts / UPCitemdb.

Requiere tu API key de Serper guardada en ~/inventario/.serper_key
(una sola linea con la clave, nada mas).

Uso:
  cd ~/inventario
  python3 buscar_imagenes_serper.py --limite 20      # prueba con 20 primero
  python3 buscar_imagenes_serper.py                  # procesa todos los pendientes
"""
import sqlite3, sys, os, time, json, urllib.request, urllib.error

DB = os.path.expanduser('~/inventario/inventario.db')
KEY_FILE = os.path.expanduser('~/inventario/.serper_key')

LIMITE = None
if '--limite' in sys.argv:
    try:
        LIMITE = int(sys.argv[sys.argv.index('--limite') + 1])
    except (IndexError, ValueError):
        print("Uso: --limite <numero>")
        sys.exit(1)

# ── Leer la API key ─────────────────────────────────────────────────────────
if not os.path.exists(KEY_FILE):
    print("ERROR: no se encontro " + KEY_FILE)
    print("Crea el archivo con tu API key de Serper:")
    print('  echo "TU_API_KEY" > ' + KEY_FILE)
    print("  chmod 600 " + KEY_FILE)
    sys.exit(1)

with open(KEY_FILE) as f:
    API_KEY = f.read().strip()

if not API_KEY:
    print("ERROR: " + KEY_FILE + " esta vacio")
    sys.exit(1)

print("API key cargada (" + API_KEY[:6] + "..." + API_KEY[-4:] + ")")
print()


def buscar_imagen_serper(query):
    """Busca en Serper.dev Images y devuelve la primera URL de imagen valida."""
    url = "https://google.serper.dev/images"
    body = json.dumps({"q": query, "num": 5}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RuntimeError("CUOTA_AGOTADA")
        if e.code in (401, 403):
            raise RuntimeError("API_KEY_INVALIDA")
        return None
    except Exception:
        return None

    imagenes = data.get("images", [])
    for img in imagenes:
        candidato = img.get("imageUrl")
        if candidato and validar_imagen(candidato):
            return candidato
    return None


def validar_imagen(url):
    """Verifica con un HEAD request que la URL realmente sirva una imagen."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            content_type = r.headers.get("Content-Type", "")
            return r.status == 200 and content_type.startswith("image/")
    except Exception:
        return False


# ── Proceso principal ───────────────────────────────────────────────────────
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
    SELECT id, nombre, marca
    FROM productos
    WHERE imagen_url LIKE 'data:image/svg%'
    ORDER BY id
""")
pendientes = cur.fetchall()
if LIMITE:
    pendientes = pendientes[:LIMITE]

total = len(pendientes)
print("Productos con placeholder (pendientes de foto real): " + str(total))
if total == 0:
    print("No hay nada pendiente. Todos los productos ya tienen foto real o no existen placeholders.")
    conn.close()
    sys.exit(0)

if not LIMITE:
    resp = input("Vas a buscar imagenes para " + str(total) + " productos usando tu cuota de Serper. Continuar? (s/N): ").strip().lower()
    if resp != 's':
        print("Cancelado.")
        conn.close()
        sys.exit(0)

print()
encontradas = 0
sin_resultado = 0

try:
    for i, (pid, nombre, marca) in enumerate(pendientes, 1):
        query = (marca + " " if marca else "") + nombre

        try:
            url_imagen = buscar_imagen_serper(query)
        except RuntimeError as e:
            if str(e) == "CUOTA_AGOTADA":
                print()
                print("Se agoto la cuota de Serper (HTTP 429). Deteniendo aqui.")
                print("Progreso guardado: " + str(i - 1) + "/" + str(total))
                break
            if str(e) == "API_KEY_INVALIDA":
                print()
                print("La API key parece invalida o sin permisos (HTTP 401/403). Revisa " + KEY_FILE)
                break
            raise

        if url_imagen:
            cur.execute("UPDATE productos SET imagen_url=? WHERE id=?", (url_imagen, pid))
            encontradas += 1
        else:
            sin_resultado += 1

        if i % 10 == 0:
            conn.commit()
            print("  " + str(i) + "/" + str(total) + "  encontradas=" + str(encontradas) + "  sin_resultado=" + str(sin_resultado))

        time.sleep(0.3)  # ser cortes con la API

    conn.commit()
except KeyboardInterrupt:
    conn.commit()
    print()
    print("Pausado. Progreso guardado. Corre el script de nuevo para continuar donde se quedo.")
    conn.close()
    sys.exit(0)

conn.close()
print()
print("=" * 50)
print("Terminado.")
print("  Imagenes reales encontradas: " + str(encontradas))
print("  Sin resultado (se quedaron con el placeholder): " + str(sin_resultado))
print()
print("Reinicia el servicio para verlas:")
print("  sudo systemctl restart inventario")
