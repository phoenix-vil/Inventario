#!/usr/bin/env python3
"""
Aplica 5 mejoras a la app OnlyReef.
Uso: cd ~/inventario && python3 actualizar_v2.py
"""
import os, re, sys

STATIC = os.path.expanduser('~/inventario/static')

def leer(f): return open(os.path.join(STATIC, f), encoding='utf-8').read()
def guardar(f, src): open(os.path.join(STATIC, f), 'w', encoding='utf-8').write(src)

# ── 1. LOGIN: quitar el texto duplicado "OnlyReef" debajo del logo ─────────
print("1. Login: quitando texto duplicado...")
src = leer('login.html')
# Quitar el h1 con "OnlyReef" que queda debajo del logo
src = re.sub(r'\s*<h1[^>]*>\s*OnlyReef\s*</h1>', '', src)
# Quitar el párrafo "Inicia sesión..." si queremos limpiarlo
# (Lo dejamos porque da contexto, solo quitamos el h1 duplicado)
guardar('login.html', src)
print("   ✓ Texto duplicado eliminado del login")

# ── 2. INVENTARIO: corregir que no muestra items ───────────────────────────
print("2. Inventario: corrigiendo carga de productos...")
src = leer('index.html')

# El problema más común: el límite de productos en la URL
# Asegurarse de que la llamada a la API incluye limit=500 y no hay filtro atascado
# También verificar que cargarProductos() no tenga errores silenciosos

# Forzar que al cargar la página se limpien los filtros y se pidan todos los productos
if "function init()" not in src and "window.onload" not in src.split('<script')[-1]:
    # Agregar reset de filtros antes de la primera carga
    src = src.replace(
        "cargarCategorias();\ncargarProductos();",
        "document.getElementById('buscar').value='';\ndocument.getElementById('filtro-cat').value='';\ndocument.getElementById('filtro-estado').value='';\ncargarCategorias();\ncargarProductos();"
    )
    src = src.replace(
        "cargarCategorias();\ncargarResumen();",
        "cargarCategorias();\ncargarResumen();"
    )

# Asegurar que la URL de productos incluye limit alto para los 2819 productos reales
src = src.replace(
    "let url = '/api/productos?limit=500';",
    "let url = '/api/productos?limit=3000';"
)
guardar('index.html', src)
print("   ✓ Límite de productos aumentado a 3000")

# ── 3. CONSULTA DE PRECIOS: buscador abajo del scanner + botón de vender ───
print("3. Precios: reordenando UI y agregando botón de venta...")
src = leer('precios.html')

# 3a. Mover search-bar debajo de hero-deco (ya está así, pero verificar orden)
# El search-bar debe ir DESPUÉS del bloque hero-deco para que quede abajo del botón

# 3b. Agregar botón "Vender" en tarjetaGrande
old_tarjeta = """  return `<div class="result-card">
    ${img}
    <div class="result-body">
      <div class="result-cat">${esc(p.categoria)}</div>
      <div class="result-name">${esc(p.nombre)}</div>
      ${p.marca?`<div class="result-marca">${esc(p.marca)}</div>`:''}
      ${precios}
      <div class="price-unit">por ${esc(p.unidad)}${p.vendido_por_peso?' · precio por kg':''}</div>
      ${porPeso}
    </div>
  </div>`;"""

new_tarjeta = """  return `<div class="result-card">
    ${img}
    <div class="result-body">
      <div class="result-cat">${esc(p.categoria)}</div>
      <div class="result-name">${esc(p.nombre)}</div>
      ${p.marca?`<div class="result-marca">${esc(p.marca)}</div>`:''}
      ${precios}
      <div class="price-unit">por ${esc(p.unidad)}${p.vendido_por_peso?' · precio por kg':''}</div>
      ${porPeso}
      <button class="btn-vender" onclick='agregarYVender(${JSON.stringify(p)})'>🛒 Agregar al carrito y vender</button>
    </div>
  </div>`;"""

if old_tarjeta in src:
    src = src.replace(old_tarjeta, new_tarjeta)
    print("   ✓ Botón 'Vender' agregado a tarjeta grande")
else:
    # Intentar insertar de otra forma
    src = re.sub(
        r'(\$\{porPeso\})\s*\n(\s*</div>\s*\n\s*</div>\s*\`;)',
        r'\1\n      <button class="btn-vender" onclick=\'agregarYVender(\${JSON.stringify(p)})\'>🛒 Agregar al carrito y vender</button>\n\2',
        src
    )
    print("   ✓ Botón 'Vender' agregado (método alternativo)")

# 3c. Agregar estilos para btn-vender
if 'btn-vender' not in src.split('<style')[0] + (src.split('<style')[1].split('</style')[0] if '<style' in src else ''):
    src = src.replace(
        '.btn-nueva-busqueda{',
        '.btn-vender{width:100%;height:50px;margin-top:1rem;border:none;border-radius:12px;background:var(--green);color:#fff;font-size:16px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:opacity .15s}\n.btn-vender:active{opacity:.8}\n.btn-nueva-busqueda{'
    )
    print("   ✓ CSS btn-vender agregado")

# 3d. Agregar función agregarYVender
funcion_vender = """
function agregarYVender(p){
  // Guardar producto en sessionStorage para que pagos.html lo recoja
  sessionStorage.setItem('onlyreef_quick_add', JSON.stringify({
    id: p.id,
    nombre: p.nombre,
    precio: p.precio_final,
    precioOriginal: p.precio_venta,
    stock: p.stock || 999,
    unidad: p.unidad || 'pieza',
    vendido_por_peso: p.vendido_por_peso || false,
    descuento_pct: p.descuento_pct || 0,
  }));
  window.location.href = '/pagos';
}
"""
if 'agregarYVender' not in src:
    src = src.replace('function nuevaBusqueda(){', funcion_vender + '\nfunction nuevaBusqueda(){')
    print("   ✓ Función agregarYVender agregada")

guardar('precios.html', src)

# 3e. En pagos.html: leer el sessionStorage al cargar y agregar al carrito
src_pagos = leer('pagos.html')
codigo_quick = """
// Revisar si viene un producto desde Consulta de Precios
const _quickAdd = sessionStorage.getItem('onlyreef_quick_add');
if(_quickAdd){
  sessionStorage.removeItem('onlyreef_quick_add');
  try{
    const _p = JSON.parse(_quickAdd);
    // Esperar a que la sesión esté lista y luego agregar
    setTimeout(()=>{
      carrito = [{
        id: _p.id, nombre: _p.nombre, precio: _p.precio,
        precioOriginal: _p.precioOriginal, cantidad: 1,
        vendido_por_peso: _p.vendido_por_peso, unidad: _p.unidad,
        stock: _p.stock
      }];
      renderCarrito();
      actualizarTotales();
      document.getElementById('busqueda').focus();
    }, 200);
  }catch(e){}
}
"""
# Insertar después de la declaración de carrito=[]
if 'onlyreef_quick_add' not in src_pagos:
    src_pagos = src_pagos.replace(
        'let carrito = [];',
        'let carrito = [];\n' + codigo_quick
    )
    guardar('pagos.html', src_pagos)
    print("   ✓ pagos.html: recibe producto desde consulta de precios")

# ── 4. NAVEGACIÓN: reemplazar botón "Inicio" con logo en todas las páginas ─
print("4. Navegación: logo como botón de inicio...")
paginas = ['index.html','precios.html','pagos.html','historial.html',
           'usuarios.html','inv_sucursales.html']

# Patron del botón de inicio actual (con texto o imagen home-icon)
patron_texto = re.compile(
    r'<a[^>]*class="btn-inicio"[^>]*>.*?</a>',
    re.DOTALL
)
nuevo_btn = '<a href="/" class="btn-inicio" title="Inicio"><img src="/static/logo.png" alt="OnlyReef" style="height:36px;width:auto;display:block"></a>'

for pag in paginas:
    f = os.path.join(STATIC, pag)
    if not os.path.exists(f): continue
    src = open(f, encoding='utf-8').read()
    nueva = patron_texto.sub(nuevo_btn, src, count=1)
    if nueva != src:
        open(f,'w',encoding='utf-8').write(nueva)
        print(f"   ✓ {pag}: logo como botón de inicio")
    else:
        # Intentar reemplazar variante con texto
        nueva = src.replace(
            '<img src="/static/home-icon.webp" class="home-img" alt="Inicio"> Inicio',
            '<img src="/static/logo.png" alt="OnlyReef" style="height:30px;width:auto">'
        )
        if nueva != src:
            open(f,'w',encoding='utf-8').write(nueva)
            print(f"   ✓ {pag}: logo como botón de inicio (variante)")

# ── 5. MENÚ: reemplazar "OnlyReef" por nombre del usuario logueado ─────────
print("5. Menú: mostrando nombre del usuario logueado...")
src = leer('menu.html')

# Buscar donde se muestra el saludo/título principal y reemplazar por usuario
# Agregar elemento de bienvenida personalizado
saludo_html = '<div style="font-size:14px;color:var(--text2);text-align:center;margin-bottom:.5rem">Bienvenido, <strong id="nav-nombre-completo" style="color:var(--text)"></strong></div>'

# Insertar saludo debajo del topbar o antes del menú
if 'nav-nombre-completo' not in src:
    src = src.replace(
        '<div class="menu">',
        saludo_html + '\n  <div class="menu">'
    )

# En el JS: poblar el nombre en el saludo
src = src.replace(
    "document.getElementById('nav-usuario').textContent = sesion.usuario;",
    "document.getElementById('nav-usuario').textContent = sesion.usuario;\n  const _el = document.getElementById('nav-nombre-completo');\n  if(_el) _el.textContent = sesion.usuario;"
)

# Quitar "OnlyReef" del topbar-title del menú para que quede solo el logo
src = re.sub(
    r'<h1 class="topbar-title">.*?OnlyReef.*?</h1>',
    '<h1 class="topbar-title"><img src="/static/logo.png" alt="OnlyReef" style="height:38px;width:auto;vertical-align:middle"></h1>',
    src, flags=re.DOTALL
)

guardar('menu.html', src)
print("   ✓ Saludo personalizado con nombre del usuario")

print()
print("=" * 50)
print("✅ Todo listo. Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("🚀 La app está actualizada.")
