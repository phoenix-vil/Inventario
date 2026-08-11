#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version mejorada: igual que buscar_imagenes_serper.py, pero ademas guarda un
registro (serper_log.csv) con exactamente que producto se proceso, la
busqueda usada, y el resultado - para poder revisarlo despues.

Uso:
  cd ~/inventario
  python3 buscar_imagenes_serper_v2.py --limite 20
  python3 buscar_imagenes_serper_v2.py
"""
import sqlite3, sys, os, time, json, csv, urllib.request, urllib.error
from datetime import datetime

DB = os.path.expanduser('~/inventario/inventario.db')
KEY_FILE = os.path.expanduser('~/inventario/.serper_key')
LOG_FILE = os.path.expanduser('~/inventario/serper_log.csv')

LIMITE = None
if '--limite' in sys.argv:
    try:
        LIMITE = int(sys.argv[sys.argv.index('--limite') + 1])
    except (IndexError, ValueError):
        print("Uso: --limite <numero>")
        sys.exit(1)

if not os.path.exists(KEY_FILE):
    print("ERROR: no se encontro " + KEY_FILE)
    print('  echo "TU_API_KEY" > ' + KEY_FILE)
    sys.exit(1)

with open(KEY_FILE) as f:
    API_KEY = f.read().strip()

print("API key cargada (" + API_KEY[:6] + "..." + API_KEY[-4:] + ")")
print("Registro de resultados en: " + LOG_FILE)
print()


def buscar_imagen_serper(query):
    url = "https://google.serper.dev/images"
    body = json.dumps({"q": query, "num": 5}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"}
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

    for img in data.get("images", []):
        candidato = img.get("imageUrl")
        if candidato and validar_imagen(candidato):
            return candidato
    return None


def validar_imagen(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            ct = r.headers.get("Content-Type", "")
            return r.status == 200 and ct.startswith("image/")
    except Exception:
        return False


conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("""
    SELECT id, nombre, marca FROM productos
    WHERE imagen_url LIKE 'data:image/svg%' ORDER BY id
""")
pendientes = cur.fetchall()
if LIMITE:
    pendientes = pendientes[:LIMITE]

total = len(pendientes)
print("Productos pendientes: " + str(total))
if total == 0:
    print("Nada pendiente.")
    conn.close(); sys.exit(0)

if not LIMITE:
    resp = input("Vas a consultar " + str(total) + " productos. Continuar? (s/N): ").strip().lower()
    if resp != 's':
        print("Cancelado."); conn.close(); sys.exit(0)

log_existe = os.path.exists(LOG_FILE)
log_f = open(LOG_FILE, 'a', newline='', encoding='utf-8')
log_w = csv.writer(log_f)
if not log_existe:
    log_w.writerow(['fecha', 'producto_id', 'nombre', 'marca', 'query', 'resultado', 'imagen_url'])

print()
encontradas = 0
sin_resultado = 0

try:
    for i, (pid, nombre, marca) in enumerate(pendientes, 1):
        query = (marca + " " if marca else "") + nombre
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            url_imagen = buscar_imagen_serper(query)
        except RuntimeError as e:
            if str(e) == "CUOTA_AGOTADA":
                print("\nCuota agotada. Progreso guardado: " + str(i-1) + "/" + str(total))
                break
            if str(e) == "API_KEY_INVALIDA":
                print("\nAPI key invalida. Revisa " + KEY_FILE)
                break
            raise

        if url_imagen:
            cur.execute("UPDATE productos SET imagen_url=? WHERE id=?", (url_imagen, pid))
            encontradas += 1
            log_w.writerow([ahora, pid, nombre, marca or '', query, 'ENCONTRADA', url_imagen])
            print("  [" + str(i) + "/" + str(total) + "] " + nombre[:45] + "  -> OK")
        else:
            sin_resultado += 1
            log_w.writerow([ahora, pid, nombre, marca or '', query, 'SIN_RESULTADO', ''])
            print("  [" + str(i) + "/" + str(total) + "] " + nombre[:45] + "  -> sin resultado")

        if i % 10 == 0:
            conn.commit()
            log_f.flush()

        time.sleep(0.3)

    conn.commit()
except KeyboardInterrupt:
    conn.commit()
    print("\nPausado. Progreso guardado.")
finally:
    log_f.close()

conn.close()
print()
print("=" * 50)
print("Encontradas: " + str(encontradas) + "  |  Sin resultado: " + str(sin_resultado))
print()
print("Revisa el detalle completo con:")
print("  cat ~/inventario/serper_log.csv")
print("  (o abrelo en Excel/Numbers para verlo mas comodo)")
print()
print("Reinicia el servicio para ver las imagenes nuevas:")
print("  sudo systemctl restart inventario")
