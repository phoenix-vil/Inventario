#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ajusta el menu de Configuracion:
- El boton (engranaje) ahora es visible para TODOS (no solo gerentes),
  ya que debe contener "Cerrar sesion" que todos necesitan.
- Usuarios y Sucursales dentro del menu siguen ocultos para cajeros.
- Cerrar sesion se mueve DENTRO del menu desplegable (se quita el
  boton separado que existia antes).
Uso: cd ~/inventario/static && python3 config_menu_v2.py
"""
import os, re

MENU = os.path.expanduser('~/inventario/static/menu.html')
src = open(MENU, encoding='utf-8').read()
original = src

viejo = '''    <span style="font-size:13px;color:var(--text2);white-space:nowrap">👤 <strong id="nav-usuario" style="color:var(--text)"></strong> <span id="nav-rol" style="color:var(--text2)"></span></span>
    <div style="position:relative">
      <button class="solo-gerente" onclick="toggleConfigMenu()" id="btn-config" style="display:none;height:32px;width:32px;align-items:center;justify-content:center;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:15px;cursor:pointer;flex-shrink:0" title="Configuración">⚙️</button>
      <div id="config-dropdown" style="display:none;position:absolute;top:40px;right:0;background:var(--bg2);border:0.5px solid var(--border);border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.18);min-width:170px;z-index:50;overflow:hidden">
        <a href="/usuarios" style="display:block;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">👥 Usuarios</a>
        <a href="/usuarios#sucursales" style="display:block;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px">🏪 Sucursales</a>
      </div>
    </div>
    <button onclick="logout()" style="height:32px;padding:0 12px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:13px;cursor:pointer;flex-shrink:0">Cerrar sesión</button>
  </div>'''

nuevo = '''    <span style="font-size:13px;color:var(--text2);white-space:nowrap">👤 <strong id="nav-usuario" style="color:var(--text)"></strong> <span id="nav-rol" style="color:var(--text2)"></span></span>
    <div style="position:relative">
      <button onclick="toggleConfigMenu()" id="btn-config" style="display:flex;height:32px;width:32px;align-items:center;justify-content:center;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:15px;cursor:pointer;flex-shrink:0" title="Configuración">⚙️</button>
      <div id="config-dropdown" style="display:none;position:absolute;top:40px;right:0;background:var(--bg2);border:0.5px solid var(--border);border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.18);min-width:170px;z-index:50;overflow:hidden">
        <a href="/usuarios" class="config-gerente-only" style="display:none;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">👥 Usuarios</a>
        <a href="/usuarios#sucursales" class="config-gerente-only" style="display:none;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">🏪 Sucursales</a>
        <button onclick="logout()" style="display:block;width:100%;text-align:left;padding:10px 14px;color:var(--text);background:none;border:none;font-size:14px;cursor:pointer">🚪 Cerrar sesión</button>
      </div>
    </div>
  </div>'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("1. Topbar actualizado: engranaje visible para todos, logout dentro del menu")
elif 'config-gerente-only' in src:
    print("1. * Ya estaba actualizado")
else:
    print("1. ERROR: no se encontro el bloque exacto del topbar")

# Agregar el toggle de .config-gerente-only junto al de .solo-gerente
viejo_js = "document.querySelectorAll('.solo-gerente').forEach(el => el.style.display = 'flex');"
nuevo_js = "document.querySelectorAll('.solo-gerente').forEach(el => el.style.display = 'flex');\n    document.querySelectorAll('.config-gerente-only').forEach(el => el.style.display = 'block');"

n2 = src.count(viejo_js)
if n2 == 1:
    src = src.replace(viejo_js, nuevo_js, 1)
    print("2. Visibilidad de Usuarios/Sucursales (dentro del menu) restringida a gerentes")
elif "config-gerente-only').forEach" in src:
    print("2. * Ya estaba agregado")
else:
    print("2. ERROR: no se encontro la linea exacta del toggle de solo-gerente")

if src != original:
    open(MENU, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. El engranaje ya es visible para todos; Usuarios/Sucursales")
    print("siguen ocultos para cajeros, y Cerrar sesion esta dentro del menu.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
