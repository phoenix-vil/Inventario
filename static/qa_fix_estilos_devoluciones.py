#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el estilo de devoluciones.html: copia el bloque <style>
base de historial.html (variables de color, .topbar, .container, .msg,
.overlay, .modal, .field, etc.) que NO esta en modern.css sino inline
en cada pagina.
Uso: cd ~/inventario-qa/static && python3 qa_fix_estilos_devoluciones.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

# ── 1. Extraer el bloque <style> de historial.html ──────────
hist = open(os.path.join(STATIC, 'historial.html'), encoding='utf-8').read()
m = re.search(r'<style>(.*?)</style>', hist, re.DOTALL)
if not m:
    print("ERROR: no se encontro el bloque <style> en historial.html")
    raise SystemExit(1)

estilo_base = m.group(1)
print("Bloque base extraido de historial.html: " + str(len(estilo_base)) + " bytes")

# Quitar reglas especificas de historial que no aplican aqui
# (se conservan las base: :root, topbar, container, msg, overlay, modal, field...)
lineas_filtradas = []
prefijos_omitir = ('.filtro', '.venta-item', '.tk-', '.stat', '.resumen', '.abono')
for linea in estilo_base.split('\n'):
    stripped = linea.strip()
    if any(stripped.startswith(p) for p in prefijos_omitir):
        continue
    lineas_filtradas.append(linea)
estilo_base = '\n'.join(lineas_filtradas)

# ── 2. Insertarlo en devoluciones.html ─────────────────────
ruta = os.path.join(STATIC, 'devoluciones.html')
src = open(ruta, encoding='utf-8').read()

if '--bg:#f5f4f0' in src or ':root{' in src:
    print("* devoluciones.html: ya tenia las variables base, no se hace nada")
else:
    # Insertar el bloque base ANTES del <style> propio de la pagina
    m2 = re.search(r'<style>', src)
    if not m2:
        print("ERROR: no se encontro <style> en devoluciones.html")
        raise SystemExit(1)
    nuevo_bloque = '<style>\n' + estilo_base + '\n</style>\n'
    src = src[:m2.start()] + nuevo_bloque + src[m2.start():]
    open(ruta, 'w', encoding='utf-8').write(src)
    print("OK: bloque de estilos base insertado en devoluciones.html")

# ── 3. Verificar ───────────────────────────────────────────
s = open(ruta, encoding='utf-8').read()
print()
for clave in [':root{', '.topbar{', '.container{', '.msg{', '.overlay{', '.modal{']:
    print("  contiene " + clave + " :", "SI" if clave in s else "NO")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
ok = all(x.count('{') == x.count('}') for x in scripts)
print()
print("Balance de llaves en el JS:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 55)
if ok:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Recarga con Ctrl+Shift+R.")
else:
    print("ADVERTENCIA: desbalance. NO se reinicio el servicio.")
