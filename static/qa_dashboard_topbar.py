#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Mueve el acceso al Dashboard: quita el tile de la lista y lo
coloca como boton en la barra superior, junto al de configuracion,
para que las tarjetas del menu queden alineadas.
Uso: cd ~/inventario-qa/static && python3 qa_dashboard_topbar.py
"""
import os, re

MENU = os.path.expanduser('~/inventario-qa/static/menu.html')
src = open(MENU, encoding='utf-8').read()
res = []

# ============================================================
# 1. Quitar el tile del dashboard
# ============================================================
viejo_tile = '''<a class="menu-btn solo-gerente" href="/dashboard" style="display:none">
    <div class="icon icon-pagos">📊</div>
    <div class="menu-text">
      <div class="menu-title">Dashboard</div>
      <div class="menu-desc">Ventas, ganancias y productos mas vendidos</div>
    </div>
    <div class="arrow">›</div>
  </a>
'''
if viejo_tile in src:
    src = src.replace(viejo_tile, '', 1)
    res.append("OK: tile del Dashboard removido de la lista")
elif 'href="/dashboard" style="display:none">' not in src:
    res.append("* el tile ya no estaba")
else:
    res.append("ERROR: no se encontro el tile exacto del Dashboard")

# ============================================================
# 2. Agregar el boton en la barra superior
# ============================================================
viejo_bar = '''    <div style="position:relative">
      <button onclick="toggleConfigMenu()" id="btn-config"'''
nuevo_bar = '''    <a href="/dashboard" id="btn-dashboard" class="solo-gerente" style="display:none;height:32px;width:32px;align-items:center;justify-content:center;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:15px;cursor:pointer;flex-shrink:0;text-decoration:none" title="Dashboard">📊</a>
    <div style="position:relative">
      <button onclick="toggleConfigMenu()" id="btn-config"'''
if viejo_bar in src and 'id="btn-dashboard"' not in src:
    src = src.replace(viejo_bar, nuevo_bar, 1)
    res.append("OK: boton del Dashboard agregado en la barra superior")
elif 'id="btn-dashboard"' in src:
    res.append("* el boton ya estaba en la barra")
else:
    res.append("ERROR: no se encontro la barra superior")

open(MENU, 'w', encoding='utf-8').write(src)

# ============================================================
# 3. Verificar como se muestran los elementos solo-gerente
# ============================================================
print()
for r in res:
    print(r)

print()
print("Como se activan los elementos de gerente en este archivo:")
for i, linea in enumerate(open(MENU, encoding='utf-8').read().split('\n'), 1):
    if 'solo-gerente' in linea and ('querySelectorAll' in linea or 'style.display' in linea or 'forEach' in linea):
        print("  linea " + str(i) + ": " + linea.strip()[:120])

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Ctrl+Shift+R en el menu.")
    print()
    print("IMPORTANTE: verifica que el boton 📊 aparezca como GERENTE")
    print("y que NO aparezca al entrar como operador.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
