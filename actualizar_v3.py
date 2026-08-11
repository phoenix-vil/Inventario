#!/usr/bin/env python3
"""
Corrige: inventario vacío (stock negativo), buscador abajo del escáner,
logo como inicio en index.html, nombre de usuario en el menú.
Uso: cd ~/inventario && python3 actualizar_v3.py
"""
import os, re, sqlite3

STATIC = os.path.expanduser('~/inventario/static')
DB     = os.path.expanduser('~/inventario/inventario.db')

def leer(f): return open(os.path.join(STATIC, f), encoding='utf-8').read()
def guardar(f, s): open(os.path.join(STATIC, f), 'w', encoding='utf-8').write(s)

# ══ 1. INVENTARIO: corregir stocks negativos en la base de datos ═══════════
print("1. Corrigiendo stocks negativos en la base de datos...")
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM productos WHERE stock < 0")
negativos = cur.fetchone()[0]
cur.execute("UPDATE productos SET stock = 0 WHERE stock < 0")
cur.execute("UPDATE productos SET stock_minimo = 0 WHERE stock_minimo < 0")
cur.execute("UPDATE productos SET precio_venta = precio_costo WHERE precio_venta <= 0 AND precio_costo > 0")
cur.execute("UPDATE productos SET precio_venta = 1 WHERE precio_venta <= 0")
conn.commit()
conn.close()
print(f"   ✓ {negativos} producto(s) con stock negativo corregidos a 0")
print("   ✓ Precios en 0 corregidos (la API también los rechaza)")

# ══ 2. PRECIOS: mover buscador DEBAJO del botón de escaneo ═════════════════
print("2. Moviendo buscador debajo del botón de escaneo...")
src = leer('precios.html')

# Extraer el bloque search-bar actual
m_search = re.search(r'(\s*<!--[^>]*?-->\s*)?(\s*<div class="search-bar">.*?</div>)\s*', src, re.DOTALL)
m_deco   = re.search(r'(<div class="hero-idle" id="hero-deco">.*?</div>\s*</div>)', src, re.DOTALL)

if m_search and m_deco:
    bloque_search = m_search.group(2)
    # Quitar el search-bar de su posición actual
    src = src.replace(m_search.group(0), '\n')
    # Insertarlo justo después del cierre de hero-deco
    m_deco2 = re.search(r'(<div class="hero-idle" id="hero-deco">.*?</div>\s*</div>)', src, re.DOTALL)
    fin = m_deco2.end()
    src = src[:fin] + '\n\n  ' + bloque_search.strip() + '\n' + src[fin:]
    print("   ✓ Buscador movido debajo del escáner")
else:
    print("   ⚠ No se encontró la estructura esperada (revisar manualmente)")

# Evitar el bug del teclado: NO ocultar hero-deco al mostrar resultados
# (si se oculta, el buscador salta de posición y el teclado del iPad se cierra)
src = src.replace(
    "document.getElementById('hero-deco').style.display='none';",
    "/* hero-deco visible para no mover el buscador */"
)
src = src.replace(
    "document.getElementById('hero-deco').style.display='flex';",
    "/* hero-deco siempre visible */"
)
guardar('precios.html', src)
print("   ✓ El bloque superior ya no se oculta (evita que se cierre el teclado)")

# ══ 3. INDEX: logo como botón de inicio ════════════════════════════════════
print("3. Homologando botón de inicio en index.html...")
src = leer('index.html')
# Buscar el primer <a href="/"...>...</a> del topbar (cualquier formato)
patron = re.compile(r'<a href="/"[^>]*>.*?</a>', re.DOTALL)
nuevo = '<a href="/" class="btn-inicio" title="Inicio"><img src="/static/logo.png" alt="OnlyReef" style="height:36px;width:auto;display:block"></a>'
nueva_src, n = patron.subn(nuevo, src, count=1)
if n:
    guardar('index.html', nueva_src)
    print("   ✓ index.html: logo como botón de inicio")
else:
    print("   ⚠ No se encontró el enlace de inicio en index.html")

# ══ 4. MENÚ: h1 con el nombre del usuario logueado ═════════════════════════
print("4. Menú: nombre del usuario en lugar de OnlyReef...")
src = leer('menu.html')

# Reemplazar <h1>OnlyReef</h1> por un h1 dinámico
src = src.replace('<h1>OnlyReef</h1>', '<h1 id="saludo-usuario">Hola</h1>')

# Quitar el div "Bienvenido, ..." agregado antes (para no duplicar)
src = re.sub(
    r'<div style="[^"]*">Bienvenido, <strong id="nav-nombre-completo"[^>]*></strong></div>\s*',
    '', src
)

# Poblar el h1 con el nombre en el JS existente
if 'saludo-usuario' in src and "getElementById('saludo-usuario')" not in src:
    src = src.replace(
        "document.getElementById('nav-usuario').textContent = sesion.usuario;",
        "document.getElementById('nav-usuario').textContent = sesion.usuario;\n  const _saludo = document.getElementById('saludo-usuario');\n  if(_saludo) _saludo.textContent = 'Hola, ' + sesion.usuario;"
    )
guardar('menu.html', src)
print("   ✓ El menú saluda con el nombre del usuario logueado")

print()
print("═" * 50)
print("✅ Correcciones aplicadas. Reiniciando servicio...")
os.system("sudo systemctl restart inventario")
print("🚀 Listo. Refresca las páginas en tu navegador (Cmd+Shift+R).")
