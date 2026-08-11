#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Corrige el texto claro de forma robusta: en vez de variables CSS
(que fallaron), fuerza el color directamente en cada elemento via DOM,
inmediatamente despues de insertar el HTML.
2. Cambia el formato del descuento por item: quita el %, deja solo el
monto, en su propia linea, con la palabra "Descuento".
Uso: cd ~/inventario-qa/static && python3 qa_fix_definitivo_v2.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

def procesar(nombre, nombre_funcion_html):
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    cambios = []

    # ---- 1. Forzar color directo via DOM (reemplaza el intento anterior fallido) ----
    viejo_innerhtml = "contenedor.innerHTML = " + nombre_funcion_html + "(v);\n  document.body.appendChild(contenedor);"
    nuevo_innerhtml = ("contenedor.innerHTML = " + nombre_funcion_html + "(v);\n"
                       "  contenedor.querySelectorAll('.tk-sub, .tk-foot, .tk-negocio, .tk-line, .tk-total').forEach(function(el){ el.style.color = '#000000'; });\n"
                       "  contenedor.querySelectorAll('.tk-desc').forEach(function(el){ el.style.color = '#a32d2d'; });\n"
                       "  contenedor.querySelectorAll('.tk-ahorro').forEach(function(el){ el.style.color = '#3b6d11'; });\n"
                       "  document.body.appendChild(contenedor);")
    if viejo_innerhtml in src:
        src = src.replace(viejo_innerhtml, nuevo_innerhtml, 1)
        cambios.append('color forzado via DOM (metodo robusto)')
    elif "el.style.color = '#000000'" in src:
        cambios.append('* color ya forzado via DOM')
    else:
        print("ERROR " + nombre + ": no se encontro el bloque del contenedor (paso 1)")

    # ---- 2. Cambiar formato del descuento por item ----
    viejo_items = '''  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    const tieneDescItem = it.precio_original!=null && it.precio_original>it.precio_unitario;
    const badgeDesc = tieneDescItem
      ? ` <span style="color:#a32d2d;font-weight:600">(-${Math.round((1-it.precio_unitario/it.precio_original)*100)}%, -${money(it.ahorro)})</span>`
      : '';
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}${badgeDesc}</span><span>${money(it.importe)}</span></div>`;
  });'''

    nuevo_items = '''  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    const tieneDescItem = it.precio_original!=null && it.precio_original>it.precio_unitario;
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(it.importe)}</span></div>`;
    if(tieneDescItem){
      html+=`<div class="tk-line tk-desc"><span>Descuento</span><span>-${money(it.ahorro)}</span></div>`;
    }
  });'''

    if viejo_items in src:
        src = src.replace(viejo_items, nuevo_items, 1)
        cambios.append('formato de descuento por item cambiado (solo monto, linea separada)')
    elif 'tk-desc"><span>Descuento</span>' in src:
        cambios.append('* formato de descuento ya estaba cambiado')
    else:
        print("ERROR " + nombre + ": no se encontro el bloque de items (paso 2)")

    if cambios:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios:
            print("OK " + nombre + ": " + c)
    return len(cambios) > 0

r1 = procesar('pagos.html', 'generarTicketHTML')
print()
r2 = procesar('historial.html', 'ticketHTML')

print()
ok_total = True
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 55)
if ok_total:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El color se fuerza directamente por elemento (metodo robusto),")
    print("y el descuento por item ahora es una linea separada con 'Descuento' y el monto.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
