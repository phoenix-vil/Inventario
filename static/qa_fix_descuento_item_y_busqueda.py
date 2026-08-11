#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Descuento por articulo en $: se restaba el monto completo al
    PRECIO UNITARIO, asi que con 4 piezas descontaba 4 veces.
    Ahora el monto se reparte entre la cantidad del articulo.
 2. Al agregar un producto ya no se borra el texto buscado: se
    conserva y se vuelve a seleccionar, para seguir agregando.
Uso: cd ~/inventario-qa/static && python3 qa_fix_descuento_item_y_busqueda.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
res = []

# ============================================================
# 1. Descuento por articulo en $: repartir entre la cantidad
# ============================================================
viejo = '''  if(modoDescItem==='monto'){
    if(valor>c.precioOriginal){ msg.className='msg error show'; msg.textContent='El monto no puede ser mayor al precio original'; return; }
    nuevoPrecio = Math.round((c.precioOriginal - valor) * 100) / 100;
  }else{'''
nuevo = '''  if(modoDescItem==='monto'){
    const cantItem = c.cantidad || 1;
    const totalOriginal = c.precioOriginal * cantItem;
    if(valor > totalOriginal){ msg.className='msg error show'; msg.textContent='El monto no puede ser mayor a ' + money(totalOriginal) + ' (' + cantItem + ' x ' + money(c.precioOriginal) + ')'; return; }
    nuevoPrecio = Math.round((c.precioOriginal - (valor / cantItem)) * 100) / 100;
  }else{'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK: el descuento en $ ahora se reparte entre la cantidad")
elif 'const totalOriginal = c.precioOriginal * cantItem;' in src:
    res.append("* el descuento en $ ya estaba corregido")
else:
    res.append("ERROR: no se encontro el bloque del descuento por articulo")

# --- que el modal muestre la cantidad y el total del articulo ---
viejo_lbl = "  document.getElementById('item-desc-nombre').textContent = c.nombre + ' — Precio original: ' + money(c.precioOriginal);"
nuevo_lbl = "  document.getElementById('item-desc-nombre').textContent = c.nombre + ' — ' + (c.cantidad || 1) + ' x ' + money(c.precioOriginal) + ' = ' + money(c.precioOriginal * (c.cantidad || 1));"
if viejo_lbl in src:
    src = src.replace(viejo_lbl, nuevo_lbl, 1)
    res.append("OK: el modal muestra cantidad y total del articulo")
elif "' = ' + money(c.precioOriginal * (c.cantidad || 1))" in src:
    res.append("* el modal ya mostraba el total")

# ============================================================
# 2. Conservar la busqueda al agregar
# ============================================================
viejo_lb = '''function limpiarBusqueda(){
  document.getElementById('buscar').value='';
  document.getElementById('resultados').innerHTML='';
}'''
nuevo_lb = '''function limpiarBusqueda(){
  const inp = document.getElementById('buscar');
  inp.focus();
  inp.select();
}'''
if viejo_lb in src:
    src = src.replace(viejo_lb, nuevo_lb, 1)
    res.append("OK: la busqueda se conserva y queda seleccionada al agregar")
elif 'inp.select();' in src:
    res.append("* la busqueda ya se conservaba")
else:
    res.append("ERROR: no se encontro limpiarBusqueda")

open(PAGOS, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print()
    print("PRUEBA EL CASO DEL BUG:")
    print("  4 piezas de un producto -> descuento en $ de 10")
    print("  Antes: descontaba $40 (10 por pieza)")
    print("  Ahora: descuenta $10 en total")
    print()
    print("Y en la busqueda: agrega un producto y confirma que el texto")
    print("sigue ahi, seleccionado, listo para escribir otra busqueda.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
