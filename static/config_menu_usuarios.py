#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1. Quita el tile de "Usuarios" de la lista principal del menu.
2. Agrega un boton de engranaje (Configuracion) en la esquina superior
   derecha, visible solo para gerentes, con un menu desplegable:
   Usuarios -> Sucursales.
3. Agrega el ancla #sucursales en usuarios.html para que el enlace
   salte directo a esa seccion.
Uso: cd ~/inventario/static && python3 config_menu_usuarios.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario/static')

# ================================================================
# 1. menu.html: quitar el tile de Usuarios
# ================================================================
print("1. Quitando el tile de Usuarios de la lista...")
menu_path = os.path.join(STATIC, 'menu.html')
src = open(menu_path, encoding='utf-8').read()
original = src

viejo_tile = '''  <a class="menu-btn solo-gerente" href="/usuarios" id="card-usuarios" style="display:none">
    <div class="icon icon-pagos">👥</div>
    <div class="menu-text">
      <div class="menu-title">Usuarios</div>
      <div class="menu-desc">Mantenimiento de operadores (solo gerentes)</div>
    </div>
    <div class="arrow">›</div>
  </a>
'''

n1 = src.count(viejo_tile)
if n1 == 1:
    src = src.replace(viejo_tile, '', 1)
    print("   OK tile de Usuarios eliminado de la lista")
elif 'id="card-usuarios"' not in src:
    print("   * Ya estaba quitado")
else:
    print("   ERROR: no se encontro el tile exacto")

# ================================================================
# 2. menu.html: agregar boton de engranaje + menu desplegable
# ================================================================
viejo_topbar = '''    <span style="font-size:13px;color:var(--text2);white-space:nowrap">👤 <strong id="nav-usuario" style="color:var(--text)"></strong> <span id="nav-rol" style="color:var(--text2)"></span></span>
    <button onclick="logout()" style="height:32px;padding:0 12px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:13px;cursor:pointer;flex-shrink:0">Cerrar sesión</button>
  </div>'''

nuevo_topbar = '''    <span style="font-size:13px;color:var(--text2);white-space:nowrap">👤 <strong id="nav-usuario" style="color:var(--text)"></strong> <span id="nav-rol" style="color:var(--text2)"></span></span>
    <div style="position:relative">
      <button class="solo-gerente" onclick="toggleConfigMenu()" id="btn-config" style="display:none;height:32px;width:32px;align-items:center;justify-content:center;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:15px;cursor:pointer;flex-shrink:0" title="Configuración">⚙️</button>
      <div id="config-dropdown" style="display:none;position:absolute;top:40px;right:0;background:var(--bg2);border:0.5px solid var(--border);border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.18);min-width:170px;z-index:50;overflow:hidden">
        <a href="/usuarios" style="display:block;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">👥 Usuarios</a>
        <a href="/usuarios#sucursales" style="display:block;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px">🏪 Sucursales</a>
      </div>
    </div>
    <button onclick="logout()" style="height:32px;padding:0 12px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:13px;cursor:pointer;flex-shrink:0">Cerrar sesión</button>
  </div>'''

n2 = src.count(viejo_topbar)
if n2 == 1:
    src = src.replace(viejo_topbar, nuevo_topbar, 1)
    print("2. Boton de Configuracion (engranaje) agregado al topbar")
elif 'btn-config' in src:
    print("2. * Ya existia")
else:
    print("2. ERROR: no se encontro el topbar exacto")

# ================================================================
# 3. menu.html: agregar el JS de abrir/cerrar el menu desplegable
# ================================================================
if 'function toggleConfigMenu' not in src:
    js_dropdown = '''
function toggleConfigMenu(){
  const d = document.getElementById('config-dropdown');
  if(d) d.style.display = (d.style.display === 'block') ? 'none' : 'block';
}
document.addEventListener('click', function(e){
  const btn = document.getElementById('btn-config');
  const dd = document.getElementById('config-dropdown');
  if(dd && dd.style.display === 'block' && btn && !btn.contains(e.target) && !dd.contains(e.target)){
    dd.style.display = 'none';
  }
});
'''
    marcador = '</script>'
    idx = src.rfind(marcador)
    if idx != -1:
        src = src[:idx] + js_dropdown + src[idx:]
        print("3. JS del menu desplegable agregado")
    else:
        print("3. ERROR: no se encontro '</script>' para insertar el JS")
else:
    print("3. * El JS ya existia")

if src != original:
    open(menu_path, 'w', encoding='utf-8').write(src)
    print("   menu.html guardado.")

# ================================================================
# 4. usuarios.html: agregar el ancla id="sucursales"
# ================================================================
print()
print("4. Agregando ancla #sucursales en usuarios.html...")
usuarios_path = os.path.join(STATIC, 'usuarios.html')
usrc = open(usuarios_path, encoding='utf-8').read()

viejo_anchor = '<div class="section-title">Sucursales</div>'
nuevo_anchor = '<div class="section-title" id="sucursales">Sucursales</div>'

n4 = usrc.count(viejo_anchor)
if n4 == 1:
    usrc = usrc.replace(viejo_anchor, nuevo_anchor, 1)
    open(usuarios_path, 'w', encoding='utf-8').write(usrc)
    print("   OK ancla agregada")
elif 'id="sucursales"' in usrc:
    print("   * Ya existia")
else:
    print("   ERROR: no se encontro el section-title exacto")

# ================================================================
# Verificar y reiniciar
# ================================================================
print()
scripts_menu = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok_menu = all(s.count('{') == s.count('}') for s in scripts_menu)
print("Balance de llaves en menu.html:", "OK" if ok_menu else "DESBALANCEADO")

print()
print("=" * 55)
if ok_menu:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. El boton de engranaje aparece solo para gerentes,")
    print("con Usuarios y Sucursales como opciones dentro.")
else:
    print("ADVERTENCIA: desbalance de llaves en menu.html. NO se reinicio el servicio.")
