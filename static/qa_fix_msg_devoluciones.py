#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega las reglas .msg a devoluciones.html (no estaban porque
historial.html no las usa) y corrige el uso de 'success' por 'ok',
que es la clase real de la app.
Uso: cd ~/inventario-qa/static && python3 qa_fix_msg_devoluciones.py
"""
import os, re

RUTA = os.path.expanduser('~/inventario-qa/static/devoluciones.html')
src = open(RUTA, encoding='utf-8').read()
cambios = []

# ── 1. Agregar las reglas .msg ─────────────────────────────
if '.msg{' in src:
    cambios.append('* las reglas .msg ya existian')
else:
    reglas = ('.msg{padding:10px;border-radius:8px;font-size:13px;margin-top:8px;display:none}\n'
              '.msg.show{display:block}\n'
              '.msg.error{background:var(--red-bg);color:var(--red)}\n'
              '.msg.ok{background:var(--green-bg);color:var(--green)}\n')
    m = re.search(r'<style>', src)
    if m:
        src = src[:m.end()] + '\n' + reglas + src[m.end():]
        cambios.append('reglas .msg agregadas')
    else:
        print("ERROR: no se encontro <style>")

# ── 2. Corregir 'success' por 'ok' ─────────────────────────
if "'msg success show'" in src:
    src = src.replace("'msg success show'", "'msg ok show'")
    cambios.append("clase 'success' corregida a 'ok'")
elif "'msg ok show'" in src:
    cambios.append("* la clase ya usaba 'ok'")

open(RUTA, 'w', encoding='utf-8').write(src)

print()
for c in cambios:
    print("OK " + c if not c.startswith('*') else c)

# ── Verificar ──────────────────────────────────────────────
s = open(RUTA, encoding='utf-8').read()
print()
for clave in ['.msg{', '.msg.show', '.msg.error', '.msg.ok']:
    print("  contiene " + clave + " :", "SI" if clave in s else "NO")
print("  usa 'msg success' (no deberia):", "SI" if 'msg success' in s else "NO")

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
