#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega un boton de descuento por articulo en el carrito del punto de venta.
No requiere autorizacion de gerente (libre para cualquier cajero).
Reutiliza el sistema visual existente (precio tachado + badge de %).
Uso: cd ~/inventario && python3 agregar_descuento_item.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar el boton de descuento en cada renglon del carrito
# ================================================================
viejo_boton = '''      <div class="ci-importe">${money(importe)}</div>
      <button class="ci-del" onclick="quitar(${c.id})">🗑</button>
    </div>`;'''

nuevo_boton = '''      <div class="ci-importe">${money(importe)}</div>
      <button class="ci-desc-btn" onclick="descuentoItem(${c.id})" title="Descuento a este artículo">🏷</button>
      <button class="ci-del" onclick="quitar(${c.id})">🗑</button>
    </div>`;'''

src, n1 = re.subn(re.escape(viejo_boton), nuevo_boton, src)
print("1. Boton de descuento agregado al renglon del carrito:", n1 > 0)

# ================================================================
# 2. Agregar la funcion descuentoItem() justo antes de renderCarrito
# ================================================================
funcion_nueva = '''function descuentoItem(id){
  const c = carrito.find(x=>x.id===id);
  if(!c) return;
  const actual = (c.precioOriginal && c.precioOriginal>c.precio) ? Math.round((1-c.precio/c.precioOriginal)*100) : 0;
  const pctStr = prompt(`Descuento (%) para "${c.nombre}"\\nPrecio original: ${money(c.precioOriginal)}`, actual || '');
  if(pctStr===null) return;
  const pct = parseFloat(pctStr);
  if(isNaN(pct) || pct<0 || pct>100){ alert('Porcentaje inválido (0-100)'); return; }
  c.precio = Math.round(c.precioOriginal * (1 - pct/100) * 100) / 100;
  renderCarrito();
}

'''

marcador = "function renderCarrito(){"
if "function descuentoItem" not in src:
    src = src.replace(marcador, funcion_nueva + marcador, 1)
    print("2. Funcion descuentoItem() agregada")
else:
    print("2. La funcion ya existia, se omite")

# ================================================================
# 3. Agregar el estilo CSS del boton (junto al de ci-del si existe)
# ================================================================
if '.ci-desc-btn' not in src:
    patron_ci_del = re.compile(r'\.ci-del\{[^}]*\}')
    m = patron_ci_del.search(src)
    if m:
        nuevo_css = m.group(0) + '\n.ci-desc-btn{background:none;border:none;color:var(--blue);cursor:pointer;font-size:15px;padding:4px}'
        src = src[:m.start()] + nuevo_css + src[m.end():]
        print("3. Estilo .ci-desc-btn agregado")
    else:
        print("3. ADVERTENCIA: no se encontro .ci-del para insertar el estilo junto a el")
else:
    print("3. El estilo ya existia, se omite")

# ================================================================
# Guardar y verificar
# ================================================================
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
    print("Listo. Cada articulo del carrito ahora tiene un boton 🏷 para descuento individual.")
else:
    print("ADVERTENCIA: desbalance de llaves, NO se reinicio el servicio.")
