#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega una tarjeta de "Cuentas por cobrar" al Dashboard.
Corre DESPUES de creditos_backend.py
Uso: cd ~/inventario/static && python3 creditos_dashboard.py
"""
import os, re

DASH = os.path.expanduser('~/inventario/static/dashboard.html')
src = open(DASH, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar tarjeta "Cuentas por cobrar" (independiente del periodo,
#    es un saldo acumulado, no algo que varie por Hoy/Semana/Mes)
# ================================================================
viejo = '''  <div class="chart-card">'''

nuevo = '''  <div class="card" style="padding:1rem 1.25rem;margin-bottom:1.25rem;display:flex;justify-content:space-between;align-items:center">
    <div>
      <div style="font-size:12px;color:var(--text2)">💳 Cuentas por cobrar (créditos pendientes)</div>
      <div style="font-size:22px;font-weight:800;color:var(--red)" id="st-por-cobrar">—</div>
    </div>
    <a href="/clientes" style="font-size:13px;color:var(--blue);text-decoration:none;font-weight:600">Ver clientes ›</a>
  </div>

  <div class="chart-card">'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("1. Tarjeta de Cuentas por cobrar agregada")
else:
    print("1. ADVERTENCIA: coincidencias inesperadas (" + str(n) + ")")

# ================================================================
# 2. Cargar el dato al iniciar la pagina
# ================================================================
if 'st-por-cobrar' in src and 'cargarCuentasPorCobrar' not in src:
    funcion = '''
async function cargarCuentasPorCobrar(){
  try{
    const r = await authFetch('/api/clientes-resumen');
    const d = await r.json();
    document.getElementById('st-por-cobrar').textContent = money(d.total_por_cobrar);
  }catch(e){
    document.getElementById('st-por-cobrar').textContent = '—';
  }
}
'''
    src = src.replace('cargarTodo();\ncargarSerie();', funcion + '\ncargarTodo();\ncargarSerie();\ncargarCuentasPorCobrar();')
    print("2. Funcion cargarCuentasPorCobrar() agregada y enganchada al inicio")
else:
    print("2. * Ya existia o no se encontro el punto de enganche")

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
    print("Listo. El Dashboard ahora muestra Cuentas por cobrar.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
