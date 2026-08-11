#!/usr/bin/env python3
"""
1. Agrega el logo de OnlyReef arriba de "Hola, usuario"
2. Reordena la barra superior: sucursal como badge a la izquierda,
   usuario+rol al centro/derecha con espacio, botón de cerrar sesión al final.
Uso: cd ~/inventario && python3 fix_menu_logo_topbar.py
"""
import os, re

MENU = os.path.expanduser('~/inventario/static/menu.html')
src = open(MENU, encoding='utf-8').read()
original = src

# ══ 1. Reemplazar la barra superior completa ═══════════════════════════════
patron_bar = re.compile(
    r'<div style="background:var\(--bg2\).*?</div>\s*(?=<div class="header">)',
    re.DOTALL
)

nueva_bar = '''<div style="background:var(--bg2);border-bottom:0.5px solid var(--border);padding:.75rem 1.25rem;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
  <span id="nav-sucursal" style="font-size:12px;font-weight:600;color:var(--blue);background:var(--blue-bg);padding:5px 12px;border-radius:20px;white-space:nowrap;display:none"></span>
  <div style="display:flex;align-items:center;gap:12px;margin-left:auto">
    <span style="font-size:13px;color:var(--text2);white-space:nowrap">👤 <strong id="nav-usuario" style="color:var(--text)"></strong> <span id="nav-rol" style="color:var(--text2)"></span></span>
    <button onclick="logout()" style="height:32px;padding:0 12px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-size:13px;cursor:pointer;flex-shrink:0">Cerrar sesión</button>
  </div>
</div>

'''

if patron_bar.search(src):
    src = patron_bar.sub(nueva_bar, src, count=1)
    print("✓ Barra superior reordenada (sucursal en badge, usuario+rol con espacio, botón al final)")
else:
    print("⚠ No se encontró la barra superior con el patrón esperado")

# ══ 2. Agregar el logo arriba de "Hola, usuario" ════════════════════════════
patron_header = re.compile(
    r'(<div class="header">\s*)(<h1 id="saludo-usuario">Hola</h1>)'
)
nuevo_header = (
    r'\1<img src="/static/logo.png" alt="OnlyReef" '
    r'style="height:72px;width:auto;margin-bottom:.75rem">\n  \2'
)

if patron_header.search(src):
    src = patron_header.sub(nuevo_header, src, count=1)
    print("✓ Logo agregado arriba de 'Hola, usuario'")
else:
    print("⚠ No se encontró el bloque .header con el patrón esperado")

# ══ 3. Ajustar el JS: sucursal como badge separado, rol sin duplicar ═══════
src = src.replace(
    "document.getElementById('nav-rol').textContent = '· ' + sesion.rol + (sesion.sucursal ? ' · Suc. ' + sesion.sucursal : '');",
    "document.getElementById('nav-rol').textContent = '· ' + sesion.rol;\n"
    "  const _suc = document.getElementById('nav-sucursal');\n"
    "  if(_suc && sesion.sucursal){ _suc.textContent = '🏪 Sucursal ' + sesion.sucursal; _suc.style.display='inline-block'; }"
)
print("✓ JS actualizado: sucursal se muestra como badge independiente")

# ══ 4. Ajuste responsivo: logo más chico en pantallas angostas ═════════════
if '@media(max-width:560px){' in src and 'img[alt="OnlyReef"]' not in src:
    src = src.replace(
        '.header{padding:2rem 1rem 1rem}',
        '.header{padding:2rem 1rem 1rem}\n  .header img{height:56px!important}'
    )
    print("✓ Logo se ajusta en pantallas pequeñas")

if src == original:
    print("\n⚠ No se aplicó ningún cambio. Revisa el archivo manualmente.")
else:
    open(MENU, 'w', encoding='utf-8').write(src)
    print("\n" + "="*50)
    print("✅ menu.html actualizado. Reiniciando servicio...")
    os.system("sudo systemctl restart inventario")
    print("🚀 Refresca la página principal (Cmd+Shift+R).")
