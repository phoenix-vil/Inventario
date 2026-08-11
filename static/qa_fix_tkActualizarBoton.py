#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el bug introducido en el intento anterior: la funcion
tkActualizarBotonCobrar() se llamaba desde generarCotizacion() pero
nunca se definio (el rediseno de 3 pasos elimino tkMostrar(), que era
donde se iba a insertar). Se define ahora y se aplica en verCotizacion()
(que es el lugar real donde se abre una cotizacion pasada / vendida).
Uso: cd ~/inventario-qa/static && python3 qa_fix_tkActualizarBoton.py
"""
import os, re

COT = os.path.expanduser('~/inventario-qa/static/cotizaciones.html')
src = open(COT, encoding='utf-8').read()
res = []

# ============================================================
# 1. Definir la funcion (antes de generarCotizacion, que ya la llama)
# ============================================================
if 'function tkActualizarBotonCobrar' not in src:
    ancla = 'async function generarCotizacion(){'
    funcion = '''function tkActualizarBotonCobrar(v){
  const btn = document.getElementById('btn-cobrar-pos');
  if(!btn) return;
  if(v.venta_id){
    btn.disabled = true;
    btn.textContent = '✅ Ya vendida (venta #' + v.venta_id + ')';
    btn.style.opacity = '.6';
    btn.style.cursor = 'not-allowed';
  }else{
    btn.disabled = false;
    btn.textContent = '💳 Cobrar en Punto de Venta';
    btn.style.opacity = '1';
    btn.style.cursor = 'pointer';
  }
}

'''
    if ancla in src:
        src = src.replace(ancla, funcion + ancla, 1)
        res.append("OK: funcion tkActualizarBotonCobrar definida")
    else:
        res.append("ERROR: no se encontro generarCotizacion para insertar la funcion")
else:
    res.append("* la funcion ya estaba definida")

# ============================================================
# 2. Aplicarla en verCotizacion (donde se abre una cotizacion pasada)
# ============================================================
viejo = '''async function verCotizacion(id){
  try{
    const r = await authFetch('/api/cotizaciones/'+id);
    if(!r.ok) return;
    const data = await r.json();
    cerrarHistorial();
    tkActual = data;
    tkBlobActual = null;
    document.getElementById('tk-resumen-id').textContent = 'Cotización #' + data.id + (data.cliente_nombre ? ' · ' + data.cliente_nombre : '');
    document.getElementById('tk-resumen-total').textContent = money(data.total);
    irPaso(3);
  }catch(e){}
}'''
nuevo = '''async function verCotizacion(id){
  try{
    const r = await authFetch('/api/cotizaciones/'+id);
    if(!r.ok) return;
    const data = await r.json();
    cerrarHistorial();
    tkActual = data;
    tkBlobActual = null;
    document.getElementById('tk-resumen-id').textContent = 'Cotización #' + data.id + (data.cliente_nombre ? ' · ' + data.cliente_nombre : '');
    document.getElementById('tk-resumen-total').textContent = money(data.total);
    tkActualizarBotonCobrar(data);
    irPaso(3);
  }catch(e){}
}'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK: verCotizacion aplica el bloqueo del boton al abrir una cotizacion pasada")
elif 'tkActualizarBotonCobrar(data);\n    irPaso(3);\n  }catch(e){}\n}' in src:
    res.append("* verCotizacion ya lo aplicaba")
else:
    res.append("ERROR: no se encontro verCotizacion exacta")

open(COT, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

# Verificacion extra: confirmar que ya no hay llamadas a una funcion sin definir
usa_funcion = 'tkActualizarBotonCobrar(' in src
define_funcion = 'function tkActualizarBotonCobrar(v){' in src
print("Se llama a tkActualizarBotonCobrar:", usa_funcion)
print("Esta definida la funcion:", define_funcion)

print()
print("=" * 58)
if ok and define_funcion and not any(r.startswith('ERROR') for r in res):
    print("Corregido. No requiere reiniciar el servicio (solo HTML/JS).")
    print("Prueba con Ctrl+Shift+R.")
else:
    print("Revisa los mensajes de arriba antes de probar.")
