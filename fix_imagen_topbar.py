#!/usr/bin/env python3
"""
Corrige:
  1. Límite de 500 caracteres en imagen_url (rompe el inventario con placeholders SVG)
  2. Topbar del menú: sucursal en esquina, logo centrado
Uso: cd ~/inventario && python3 fix_imagen_topbar.py
"""
import os, re

BASE   = os.path.expanduser('~/inventario')
STATIC = os.path.join(BASE, 'static')

# ══ 1. Quitar el límite de 500 caracteres en imagen_url (schemas.py) ═══════
print("1. Quitando límite de 500 caracteres en imagen_url...")
sch = os.path.join(BASE, 'schemas.py')
src = open(sch, encoding='utf-8').read()

antes = src
# Reemplazar cualquier variante con max_length=500 en imagen_url
src = re.sub(
    r'imagen_url:\s*Optional\[str\]\s*=\s*Field\([^)]*max_length=500[^)]*\)',
    'imagen_url: Optional[str] = None',
    src
)
# También si tiene Field(None, max_length=500) en otra forma
src = src.replace(
    'imagen_url: Optional[str] = Field(None, max_length=500)',
    'imagen_url: Optional[str] = None'
)

if src != antes:
    open(sch,'w',encoding='utf-8').write(src)
    print("   ✓ Límite eliminado en schemas.py")
else:
    # Buscar dónde está para diagnóstico
    for i, line in enumerate(antes.splitlines(), 1):
        if 'imagen_url' in line:
            print(f"   Línea {i}: {line.strip()}")
    print("   ⚠ No se encontró el patrón exacto — revisa las líneas de arriba")

# ══ 2. Reorganizar topbar del menú ────────────────────────────────────────
print("2. Reorganizando topbar del menú (sucursal esquina, logo centro)...")
menu = os.path.join(STATIC, 'menu.html')
src = open(menu, encoding='utf-8').read()

# Ver la estructura actual del topbar
m = re.search(r'<div class="topbar">.*?</div>\s*(?=<)', src, re.DOTALL)
if m:
    print("   Topbar actual encontrado, reemplazando...")

# Nuevo topbar: sucursal a la izquierda, logo centrado, usuario a la derecha
nuevo_topbar = '''<div class="topbar" style="display:flex;align-items:center;justify-content:space-between;padding:0 1rem;height:60px">
  <div style="flex:1;font-size:12px;color:var(--text2);white-space:nowrap">
    <span id="nav-sucursal"></span>
  </div>
  <div style="flex:0 0 auto;text-align:center">
    <img src="/static/logo.png" alt="OnlyReef" style="height:44px;width:auto;vertical-align:middle">
  </div>
  <div style="flex:1;text-align:right;font-size:12px;color:var(--text2);white-space:nowrap">
    👤 <strong id="nav-usuario" style="color:var(--text)"></strong> <span id="nav-rol"></span>
  </div>
</div>'''

# Reemplazar todo el bloque topbar existente
src_nuevo = re.sub(
    r'<div class="topbar"[^>]*>.*?</div>\s*</div>',
    nuevo_topbar,
    src, count=1, flags=re.DOTALL
)

# Si el reemplazo no funcionó (estructura distinta), intentar más simple
if src_nuevo == src:
    src_nuevo = re.sub(
        r'<div class="topbar"[^>]*>.*?</div>(?=\s*<)',
        nuevo_topbar,
        src, count=1, flags=re.DOTALL
    )

if src_nuevo != src:
    src = src_nuevo
    print("   ✓ Topbar reorganizado")
else:
    print("   ⚠ No se pudo reemplazar automáticamente el topbar")

# Poblar nav-sucursal en el JS
if 'nav-sucursal' in src and "getElementById('nav-sucursal')" not in src:
    # Agregar el poblado de sucursal donde se pobla nav-usuario
    src = src.replace(
        "document.getElementById('nav-usuario').textContent = sesion.usuario;",
        "document.getElementById('nav-usuario').textContent = sesion.usuario;\n  const _suc = document.getElementById('nav-sucursal');\n  if(_suc) _suc.textContent = sesion.sucursal ? '🏪 Sucursal ' + sesion.sucursal : '';"
    )
    print("   ✓ JS: sucursal se muestra en la esquina")

open(menu,'w',encoding='utf-8').write(src)

print()
print("═" * 50)
print("✅ Correcciones aplicadas. Reiniciando servicio...")
os.system("sudo systemctl restart inventario")

# Verificar que la API ya responde
print("\nVerificando la API...")
import time, urllib.request
time.sleep(2)
try:
    with urllib.request.urlopen("http://localhost:8000/api/productos?limit=2", timeout=8) as r:
        data = r.read().decode()
    if 'nombre' in data:
        print("   ✓ ¡El inventario ya responde correctamente!")
    else:
        print("   ⚠ Respuesta inesperada:", data[:200])
except Exception as e:
    print(f"   ⚠ Aún hay un error: {e}")
    print("   Revisa: journalctl -u inventario -n 20")

print("\n🚀 Refresca el inventario en el navegador (Cmd+Shift+R).")
