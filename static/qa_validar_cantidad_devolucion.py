#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Valida en pantalla que no se pueda devolver mas de lo disponible:
 - Al escribir, si el numero excede lo disponible se ajusta al maximo
   y se avisa (antes solo lo rechazaba el servidor al enviar).
 - Refuerza la validacion antes de enviar, con mensaje claro.
Uso: cd ~/inventario-qa/static && python3 qa_validar_cantidad_devolucion.py
"""
import os, re

RUTA = os.path.expanduser('~/inventario-qa/static/devoluciones.html')
src = open(RUTA, encoding='utf-8').read()
original = src
cambios = []

# ── 1. Agregar oninput al campo de cantidad ────────────────
viejo_input = """      + '<input type="number" class="item-cant" id="dev-' + it.producto_id + '" min="0" max="' + disp + '" step="any" placeholder="0"'
      + (disp <= 0 || cancelada ? ' disabled' : '') + '>'"""
nuevo_input = """      + '<input type="number" class="item-cant" id="dev-' + it.producto_id + '" min="0" max="' + disp + '" step="any" placeholder="0"'
      + ' data-disp="' + disp + '" data-nombre="' + esc(it.nombre).replace(/"/g, '&quot;') + '"'
      + ' oninput="validarCantidad(this)"'
      + (disp <= 0 || cancelada ? ' disabled' : '') + '>'"""
if viejo_input in src:
    src = src.replace(viejo_input, nuevo_input, 1)
    cambios.append('campo de cantidad ahora valida al escribir')
elif 'oninput="validarCantidad' in src:
    cambios.append('* el campo ya validaba al escribir')
else:
    print("ERROR: no se encontro el input de cantidad")

# ── 2. Agregar la funcion validarCantidad ──────────────────
if 'function validarCantidad' not in src:
    funcion = '''
function validarCantidad(el){
  const disp = parseFloat(el.dataset.disp || '0');
  const nombre = el.dataset.nombre || 'este artículo';
  const val = parseFloat(el.value);
  if(isNaN(val)) { limpiarMsg(); return; }
  if(val < 0){ el.value = ''; return; }
  if(val > disp){
    el.value = disp;
    mostrarMsg('Solo puedes devolver ' + disp + ' de "' + nombre + '" (es lo que queda del ticket)');
  }else{
    limpiarMsg();
  }
}
'''
    marcador = 'function recolectarItems(){'
    if marcador in src:
        src = src.replace(marcador, funcion.strip() + '\n\n' + marcador, 1)
        cambios.append('funcion validarCantidad() agregada')
    else:
        print("ERROR: no se encontro recolectarItems para insertar la funcion")
else:
    cambios.append('* validarCantidad ya existia')

# ── 3. Reforzar la validacion antes de enviar ──────────────
viejo_rec = '''function recolectarItems(){
  const items = [];
  (ventaActual.detalle || []).forEach(function(it){
    const el = document.getElementById('dev-' + it.producto_id);
    if(!el || el.disabled) return;
    const cant = parseFloat(el.value);
    if(!isNaN(cant) && cant > 0){
      items.push({producto_id: it.producto_id, cantidad: cant});
    }
  });
  return items;
}'''
nuevo_rec = '''function recolectarItems(){
  const items = [];
  const yaDev = devueltoPorProducto();
  let excedido = null;
  (ventaActual.detalle || []).forEach(function(it){
    const el = document.getElementById('dev-' + it.producto_id);
    if(!el || el.disabled) return;
    const cant = parseFloat(el.value);
    if(isNaN(cant) || cant <= 0) return;
    const disp = Math.round((it.cantidad - (yaDev[it.producto_id] || 0)) * 1000) / 1000;
    if(cant > disp + 0.0001){
      excedido = {nombre: it.nombre, disp: disp, pedido: cant};
      return;
    }
    items.push({producto_id: it.producto_id, cantidad: cant});
  });
  if(excedido){
    mostrarMsg('No puedes devolver ' + excedido.pedido + ' de "' + excedido.nombre
      + '": solo quedan ' + excedido.disp + ' por devolver');
    return null;
  }
  return items;
}'''
if viejo_rec in src:
    src = src.replace(viejo_rec, nuevo_rec, 1)
    cambios.append('validacion reforzada antes de enviar')
elif 'excedido' in src:
    cambios.append('* la validacion previa ya existia')

# ── 4. Ajustar quien llama a recolectarItems (ahora puede dar null) ──
viejo_llamada = '''  const items = recolectarItems();
  if(!items.length){ mostrarMsg('Escribe la cantidad a devolver en al menos un artículo'); return; }'''
nueva_llamada = '''  const items = recolectarItems();
  if(items === null) return;
  if(!items.length){ mostrarMsg('Escribe la cantidad a devolver en al menos un artículo'); return; }'''
if viejo_llamada in src:
    src = src.replace(viejo_llamada, nueva_llamada, 1)
    cambios.append('manejo del caso invalido agregado')
elif 'if(items === null) return;' in src:
    cambios.append('* el manejo ya existia')

if src != original:
    open(RUTA, 'w', encoding='utf-8').write(src)

print()
for c in cambios:
    print(("OK " + c) if not c.startswith('*') else c)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(x.count('{') == x.count('}') for x in scripts)
okp = all(x.count('(') == x.count(')') for x in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")
print("Balance de parentesis:", "OK" if okp else "DESBALANCEADO")

print()
print("=" * 55)
if ok and okp:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Ahora el campo se ajusta solo al maximo disponible.")
else:
    print("ADVERTENCIA: desbalance. NO se reinicio el servicio.")
