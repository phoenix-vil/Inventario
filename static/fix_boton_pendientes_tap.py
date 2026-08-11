#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige el boton de ventas en espera en el topbar:
1. La insignia roja no debe interceptar toques (pointer-events:none),
   siempre debe pasar el toque al boton de abajo.
2. Mas separacion respecto al icono de Historial, para que no se
   solapen visualmente ni sean ambiguos al tocar.
Uso: cd ~/inventario/static && python3 fix_boton_pendientes_tap.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# ================================================================
# 1. Badge: pointer-events:none (nunca bloquea el toque) + un poco
#    mas adentro para no salirse hacia el icono vecino
# ================================================================
viejo = '''    <button class="icon-btn" onclick="abrirPendientes()" title="Ventas en espera" style="position:relative">
    ⏸<span id="badge-pendientes" style="display:none;position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;font-size:10px;font-weight:700;border-radius:10px;min-width:16px;height:16px;align-items:center;justify-content:center;padding:0 3px"></span>
  </button>
  <a href="/historial" class="icon-btn" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none" title="Historial">📋</a>'''

nuevo = '''    <button class="icon-btn" onclick="abrirPendientes()" title="Ventas en espera" style="position:relative;margin-right:4px">
    ⏸<span id="badge-pendientes" style="display:none;position:absolute;top:-3px;right:-3px;background:var(--red);color:#fff;font-size:10px;font-weight:700;border-radius:10px;min-width:16px;height:16px;align-items:center;justify-content:center;padding:0 3px;pointer-events:none"></span>
  </button>
  <a href="/historial" class="icon-btn" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none" title="Historial">📋</a>'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("1. Boton corregido: badge con pointer-events:none y mas separacion")
else:
    print("1. ADVERTENCIA: no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

# ================================================================
# 2. Asegurar area de toque minima de 44x44 (estandar de accesibilidad
#    tactil de iOS) en el boton, sin cambiar su apariencia visual
# ================================================================
if '.icon-btn{' in src and 'min-width:44px' not in src:
    src = re.sub(
        r'\.icon-btn\{([^}]*)\}',
        lambda m: '.icon-btn{' + m.group(1) + ';min-width:44px;min-height:44px}' if 'min-width:44px' not in m.group(1) else m.group(0),
        src, count=1
    )
    print("2. Area minima de toque (44x44) asegurada en .icon-btn")
else:
    print("2. * Ya tenia area minima o no se encontro .icon-btn")

if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Prueba de nuevo tocando el boton de ventas en espera.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
