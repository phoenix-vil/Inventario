#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega a Punto de Venta la logica para importar los productos de
una cotizacion (via ?cotizacion=ID en la URL) al carrito, para poder
cobrarla. Solo importa articulos que SI existen en el inventario; los
personalizados (mano de obra, servicios) se omiten con un aviso.
Uso: cd ~/inventario-qa/static && python3 qa_importar_cotizacion_pagos.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()

if 'function importarCotizacion' in src:
    print("* Ya estaba agregado")
else:
    viejo = "renderCarrito();\n</script>"
    nuevo = '''renderCarrito();

// ─── Importar cotizacion (llega desde /pagos?cotizacion=ID) ─────────────
async function importarCotizacion(cotId){
  try{
    const r = await authFetch('/api/cotizaciones/'+cotId);
    if(!r.ok){ alert('No se pudo cargar la cotización #'+cotId); return; }
    const cot = await r.json();
    const detalle = cot.detalle || [];
    const itemsReales = detalle.filter(it=>it.producto_id!=null);
    const itemsPersonalizados = detalle.filter(it=>it.producto_id==null);

    let agregados = 0;
    const noEncontrados = [];
    for(const it of itemsReales){
      try{
        const rp = await authFetch('/api/pos/producto/'+it.producto_id);
        if(!rp.ok){ noEncontrados.push(it.nombre); continue; }
        const p = await rp.json();
        const existente = carrito.find(c=>c.id===p.id);
        if(existente){
          existente.cantidad += it.cantidad;
        }else{
          carrito.push({
            id:p.id, nombre:p.nombre, precio:it.precio_unitario, precioOriginal:p.precio_venta,
            cantidad:it.cantidad, vendido_por_peso:p.vendido_por_peso, unidad:p.unidad, stock:p.stock
          });
        }
        agregados++;
      }catch(e){ noEncontrados.push(it.nombre); }
    }
    renderCarrito();

    let msg = 'Cotización #'+cotId+': se importaron '+agregados+' artículo(s).';
    if(itemsPersonalizados.length){
      msg += ' '+itemsPersonalizados.length+' artículo(s) personalizado(s) no se importaron (no están en inventario): '
        + itemsPersonalizados.map(it=>it.nombre).join(', ') + '.';
    }
    if(noEncontrados.length){
      msg += ' No se encontraron en inventario: ' + noEncontrados.join(', ') + '.';
    }
    alert(msg);
  }catch(e){
    alert('Error al importar la cotización');
  }
}

(function(){
  const params = new URLSearchParams(window.location.search);
  const cotId = params.get('cotizacion');
  if(cotId) importarCotizacion(cotId);
})();
</script>'''
    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        open(PAGOS, 'w', encoding='utf-8').write(src)
        print("OK: logica de importacion de cotizacion agregada")
    else:
        print("ERROR: no se encontro el punto de insercion (coincidencias: " + str(n) + ")")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok:
    print("Este cambio es solo el HTML/JS de pagos.html, no requiere")
    print("reiniciar el servicio. Prueba con Ctrl+Shift+R.")
else:
    print("ADVERTENCIA: desbalance de llaves. Revisar antes de continuar.")
