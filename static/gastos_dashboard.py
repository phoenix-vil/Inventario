#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega dos tarjetas al Dashboard: Gastos y Ganancia neta (ganancia - gastos).
Corre DESPUES de gastos_backend.py
Uso: cd ~/inventario/static && python3 gastos_dashboard.py
"""
import os, re

DASH = os.path.expanduser('~/inventario/static/dashboard.html')
src = open(DASH, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar dos tarjetas nuevas en el stats-grid
# ================================================================
viejo = '''    <div class="stat-card">
      <div class="stat-icon">📈</div>
      <div class="stat-label">Ganancia<span id="st-margen-badge"></span></div>
      <div class="stat-value green" id="st-ganancia">—</div>
      <div class="stat-delta" id="st-ganancia-delta"></div>
    </div>'''

nuevo = '''    <div class="stat-card">
      <div class="stat-icon">📈</div>
      <div class="stat-label">Ganancia<span id="st-margen-badge"></span></div>
      <div class="stat-value green" id="st-ganancia">—</div>
      <div class="stat-delta" id="st-ganancia-delta"></div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">💸</div>
      <div class="stat-label">Gastos</div>
      <div class="stat-value red" id="st-gastos">—</div>
      <div class="stat-delta">&nbsp;</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">🏆</div>
      <div class="stat-label">Ganancia neta</div>
      <div class="stat-value" id="st-ganancia-neta">—</div>
      <div class="stat-delta">&nbsp;</div>
    </div>'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("1. Tarjetas de Gastos y Ganancia neta agregadas")
else:
    print("1. ADVERTENCIA: coincidencias inesperadas (" + str(n) + "), no se modifico el HTML")

# ================================================================
# 2. Poblar los nuevos campos en cargarResumen()
# ================================================================
viejo_js = '''    document.getElementById('st-margen-badge').textContent = d.total_vendido>0 ? ' · ' + d.margen_pct + '%' : '';'''
nuevo_js = '''    document.getElementById('st-margen-badge').textContent = d.total_vendido>0 ? ' · ' + d.margen_pct + '%' : '';

    if(d.gastos !== undefined){
      document.getElementById('st-gastos').textContent = money(d.gastos);
      const gnEl = document.getElementById('st-ganancia-neta');
      gnEl.textContent = money(d.ganancia_neta);
      gnEl.className = 'stat-value ' + (d.ganancia_neta >= 0 ? 'green' : 'red');
    }'''

n2 = src.count(viejo_js)
if n2 == 1:
    src = src.replace(viejo_js, nuevo_js, 1)
    print("2. JS actualizado para poblar Gastos y Ganancia neta")
else:
    print("2. ADVERTENCIA: coincidencias inesperadas (" + str(n2) + "), no se modifico el JS")

if src != original:
    open(DASH, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. El Dashboard ahora muestra Gastos y Ganancia neta.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
