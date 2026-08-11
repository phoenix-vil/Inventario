#!/usr/bin/env python3
"""
Corrige el botón 'Agregar al carrito y vender' de la consulta de precios.
Uso: cd ~/inventario && python3 fix_vender.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario/static')
def leer(f): return open(os.path.join(STATIC, f), encoding='utf-8').read()
def guardar(f, s): open(os.path.join(STATIC, f), 'w', encoding='utf-8').write(s)

# ══ PRECIOS.HTML ═══════════════════════════════════════════════════════════
print("Corrigiendo precios.html...")
src = leer('precios.html')

# 1. Cambiar el botón para que pase solo el ID (evita problemas con apóstrofes)
src = re.sub(
    r"<button class=\"btn-vender\" onclick='agregarYVender\(\$\{JSON\.stringify\(p\)\}\)'>.*?</button>",
    '<button class="btn-vender" onclick="agregarYVender(${p.id})">🛒 Agregar al carrito y vender</button>',
    src
)
print("   ✓ Botón corregido (ahora pasa solo el ID)")

# 2. Necesitamos que tarjetaGrande guarde el producto en una variable accesible.
#    Buscamos la función y le agregamos guardar el producto en un mapa global.
if 'let _productosCache' not in src:
    # Agregar cache global al inicio del script
    src = src.replace(
        'let ultimosCodigo=null;',
        'let ultimosCodigo=null;\nlet _productosCache={}; // guarda productos por id para el botón vender'
    )

# 3. En tarjetaGrande, guardar el producto en cache antes de renderizar
#    Insertar al inicio de la función tarjetaGrande
m = re.search(r'function tarjetaGrande\(p\)\{', src)
if m and '_productosCache[p.id]=p' not in src:
    idx = m.end()
    src = src[:idx] + '\n  _productosCache[p.id]=p;' + src[idx:]
    print("   ✓ tarjetaGrande ahora guarda el producto en cache")

# 4. También en tarjetaChica (por si hay varios resultados)
m2 = re.search(r'function tarjetaChica\(p(?:,i)?\)\{', src)
if m2 and src.count('_productosCache[p.id]=p') < 2:
    idx = m2.end()
    src = src[:idx] + '\n  _productosCache[p.id]=p;' + src[idx:]
    print("   ✓ tarjetaChica también guarda en cache")

# 5. Insertar la función agregarYVender (si no existe)
if 'function agregarYVender' not in src:
    funcion = '''
function agregarYVender(id){
  const p = _productosCache[id];
  if(!p){ alert('No se encontró el producto'); return; }
  sessionStorage.setItem('onlyreef_quick_add', JSON.stringify({
    id: p.id,
    nombre: p.nombre,
    precio: p.precio_final,
    precioOriginal: p.precio_venta,
    stock: (p.stock!=null ? p.stock : 999),
    unidad: p.unidad || 'pieza',
    vendido_por_peso: p.vendido_por_peso || false
  }));
  window.location.href = '/pagos';
}
'''
    # Insertar antes de function nuevaBusqueda o al final del script
    if 'function nuevaBusqueda' in src:
        src = src.replace('function nuevaBusqueda', funcion + '\nfunction nuevaBusqueda')
    else:
        # Insertar antes del cierre del último </script>
        idx = src.rfind('</script>')
        src = src[:idx] + funcion + '\n' + src[idx:]
    print("   ✓ Función agregarYVender agregada")
else:
    print("   • La función ya existía")

guardar('precios.html', src)

# ══ PAGOS.HTML: verificar recepción ════════════════════════════════════════
print("\nVerificando pagos.html...")
src_p = leer('pagos.html')

# Ver el bloque de recepción actual
m = re.search(r"const _quickAdd = sessionStorage\.getItem\('onlyreef_quick_add'\);.*?(?=\n\n|\nfunction|\nlet |\nconst (?!_p|_quick))", src_p, re.DOTALL)

# Reescribir el bloque de recepción de forma robusta
patron_quick = re.compile(
    r"// Revisar si viene un producto desde Consulta de Precios.*?(?=\n(?:function|let |const |async |document\.|window\.|// [A-Z]))",
    re.DOTALL
)

nuevo_bloque = '''// Revisar si viene un producto desde Consulta de Precios
(function(){
  const _quickAdd = sessionStorage.getItem('onlyreef_quick_add');
  if(!_quickAdd) return;
  sessionStorage.removeItem('onlyreef_quick_add');
  try{
    const _p = JSON.parse(_quickAdd);
    // Reintentar hasta que renderCarrito exista y la sesión esté lista
    let _try = 0;
    const _iv = setInterval(()=>{
      _try++;
      if(typeof renderCarrito === 'function' && typeof actualizarTotales === 'function'){
        clearInterval(_iv);
        carrito.push({
          id: _p.id, nombre: _p.nombre, precio: _p.precio,
          precioOriginal: _p.precioOriginal, cantidad: 1,
          vendido_por_peso: _p.vendido_por_peso, unidad: _p.unidad,
          stock: _p.stock
        });
        renderCarrito();
        actualizarTotales();
      }
      if(_try > 40) clearInterval(_iv);
    }, 100);
  }catch(e){ console.error('quick add error', e); }
})();
'''

if patron_quick.search(src_p):
    src_p = patron_quick.sub(nuevo_bloque + '\n', src_p, count=1)
    print("   ✓ Bloque de recepción reescrito (robusto)")
elif 'onlyreef_quick_add' in src_p:
    # Reemplazo más agresivo: quitar el bloque viejo entre 'let carrito = [];' y la siguiente función
    src_p = re.sub(
        r"(let carrito = \[\];)\s*\n.*?onlyreef_quick_add.*?(?=\nfunction|\nlet |\nconst (?!_)|\nasync )",
        r"\1\n" + nuevo_bloque + "\n",
        src_p, count=1, flags=re.DOTALL
    )
    print("   ✓ Bloque de recepción reemplazado")
else:
    # No existe: insertarlo después de let carrito = [];
    src_p = src_p.replace('let carrito = [];', 'let carrito = [];\n' + nuevo_bloque)
    print("   ✓ Bloque de recepción insertado")

guardar('pagos.html', src_p)

# ══ Verificar balance de llaves ════════════════════════════════════════════
print("\nVerificando sintaxis...")
for f in ['precios.html','pagos.html']:
    s = leer(f)
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    for i, sc in enumerate(scripts):
        o, c = sc.count('{'), sc.count('}')
        estado = 'OK' if o==c else '⚠ DESBALANCEADO'
        print(f"   {f} script {i+1}: {{{o} }}{c} {estado}")

print()
print("═" * 50)
print("✅ Listo. Reiniciando servicio...")
os.system("sudo systemctl restart inventario")
print("🚀 Prueba: busca un producto → 'Agregar al carrito y vender' → debe llevarte a Punto de Venta con el producto ya en el carrito.")
