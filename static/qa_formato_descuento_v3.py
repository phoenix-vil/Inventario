#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Nuevo formato del descuento por producto:
- Linea del producto: muestra el PRECIO ORIGINAL (antes del descuento)
- Linea "Descuento (X%)": muestra el PRECIO FINAL ya con descuento
  (en vez de mostrar el monto aislado del descuento)
Uso: cd ~/inventario-qa/static && python3 qa_formato_descuento_v3.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo = '''  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    const tieneDescItem = it.precio_original!=null && it.precio_original>it.precio_unitario;
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(it.importe)}</span></div>`;
    if(tieneDescItem){
      html+=`<div class="tk-line tk-desc"><span>Descuento ${Math.round((1-it.precio_unitario/it.precio_original)*100)}%</span><span>-${money(it.ahorro)}</span></div>`;
    }
  });'''

nuevo = '''  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    const tieneDescItem = it.precio_original!=null && it.precio_original>it.precio_unitario;
    if(tieneDescItem){
      const importeOriginal = it.precio_original * it.cantidad;
      const pctItem = Math.round((1-it.precio_unitario/it.precio_original)*100);
      html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(importeOriginal)}</span></div>`;
      html+=`<div class="tk-line tk-desc"><span>Descuento (${pctItem}%)</span><span>${money(it.importe)}</span></div>`;
    }else{
      html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(it.importe)}</span></div>`;
    }
  });'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": nuevo formato aplicado (original -> descuento con precio final)")
        total += 1
    elif 'importeOriginal' in src:
        print("* " + nombre + ": ya estaba en el nuevo formato")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

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
    print("Listo. Ejemplo de como se vera:")
    print("  1x 45 forceps                    $380.00")
    print("    Descuento (19%)                $307.80")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
