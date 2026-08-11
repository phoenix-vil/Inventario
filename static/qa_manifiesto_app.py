#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Crea el manifiesto (manifest.json) para que la app se pueda
instalar en Windows/Android con nombre, icono y colores propios.
2. Corrige las referencias rotas a icon-square.png (no existe) por los
touch-icon-v3 que si existen.
3. Enlaza el manifiesto en todas las paginas HTML.
Uso: cd ~/inventario-qa/static && python3 qa_manifiesto_app.py
"""
import os, re, glob

STATIC = os.path.expanduser('~/inventario-qa/static')

# ============================================================
# 1. Crear manifest.json
# ============================================================
manifest = '''{
  "name": "Only Enterprises",
  "short_name": "Only",
  "description": "Sistema de inventario y punto de venta",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f5f4f0",
  "theme_color": "#1a1a18",
  "orientation": "any",
  "icons": [
    {
      "src": "/static/touch-icon-v3-180.png",
      "sizes": "180x180",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/static/touch-icon-v3-1024.png",
      "sizes": "1024x1024",
      "type": "image/png",
      "purpose": "any"
    }
  ]
}
'''
ruta_manifest = os.path.join(STATIC, 'manifest.json')
open(ruta_manifest, 'w', encoding='utf-8').write(manifest)
print("OK: manifest.json creado")

# ============================================================
# 2 y 3. Corregir icono roto + enlazar manifiesto en cada HTML
# ============================================================
archivos = sorted(glob.glob(os.path.join(STATIC, '*.html')))
print()
for ruta in archivos:
    nombre = os.path.basename(ruta)
    src = open(ruta, encoding='utf-8').read()
    original = src
    cambios = []

    # Corregir referencias al icono inexistente
    n_icono = len(re.findall(r'/static/icon-square\.png[^"\']*', src))
    if n_icono:
        src = re.sub(r'/static/icon-square\.png[^"\']*', '/static/touch-icon-v3-180.png', src)
        cambios.append('icono corregido (' + str(n_icono) + ' ref)')

    # Enlazar manifiesto y theme-color si no existen
    if 'rel="manifest"' not in src:
        etiquetas = ('<link rel="manifest" href="/static/manifest.json">\n'
                     '<meta name="theme-color" content="#1a1a18">\n'
                     '<meta name="mobile-web-app-capable" content="yes">\n')
        m = re.search(r'<meta charset="UTF-8">\s*\n', src)
        if m:
            src = src[:m.end()] + etiquetas + src[m.end():]
            cambios.append('manifiesto enlazado')
        else:
            cambios.append('ADVERTENCIA: no se encontro <meta charset> para insertar')

    if src != original:
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": " + ", ".join(cambios))
    else:
        print("* " + nombre + ": sin cambios")

print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print()
print("Verifica que el manifiesto se sirva correctamente:")
print("  curl -s http://localhost:8001/static/manifest.json")
