#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Agrega una funcion que extrae un mensaje legible del error del
servidor (que puede venir como texto simple o como lista de errores de
validacion), en vez de mostrar "[object Object]".
2. Evita que el descuento en modo $ pueda calcular un porcentaje mayor
a 100 por errores de redondeo (la causa mas probable del 422).
Uso: cd ~/inventario-qa/static && python3 qa_fix_object_object.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Agregar funcion auxiliar para extraer mensaje de error legible
# ================================================================
if 'function extraerMensajeError' not in src:
    funcion = '''function extraerMensajeError(detail, fallback){
  if(!detail) return fallback;
  if(typeof detail === 'string') return detail;
  if(Array.isArray(detail)){
    return detail.map(function(e){
      if(typeof e === 'string') return e;
      if(e && e.msg) return e.msg;
      return JSON.stringify(e);
    }).join(' — ');
  }
  return fallback;
}

'''
    marcador = 'function setMetodo(m){'
    if marcador in src:
        src = src.replace(marcador, funcion + marcador, 1)
        cambios.append('funcion extraerMensajeError() agregada')
    else:
        print("ERROR: no se encontro 'function setMetodo(m){'")
else:
    cambios.append('* extraerMensajeError ya existia')

# ================================================================
# 2. Usar la funcion en los 3 lugares que muestran data.detail
# ================================================================
reemplazos = [
    (
        "alert(data.detail||'No se pudo dejar en espera');",
        "alert(extraerMensajeError(data.detail, 'No se pudo dejar en espera'));"
    ),
    (
        "if(!r.ok){ alert(data.detail||'No se pudo crear el cliente'); return; }",
        "if(!r.ok){ alert(extraerMensajeError(data.detail, 'No se pudo crear el cliente')); return; }"
    ),
    (
        "if(!r.ok){msg.className='msg error show';msg.textContent=data.detail||'Error al registrar venta';return;}",
        "if(!r.ok){msg.className='msg error show';msg.textContent=extraerMensajeError(data.detail, 'Error al registrar venta');return;}"
    ),
]

for viejo, nuevo in reemplazos:
    if viejo in src:
        src = src.replace(viejo, nuevo, 1)
        cambios.append('mensaje de error corregido: ' + viejo[:50] + '...')
    elif 'extraerMensajeError(data.detail' in src and viejo not in original:
        pass

# ================================================================
# 3. Evitar que el descuento en modo $ exceda 100% por redondeo
# ================================================================
viejo_calc = "pct = Math.round((valor/subtotal)*10000)/100;"
nuevo_calc = "pct = Math.min(100, Math.round((valor/subtotal)*10000)/100);"
if viejo_calc in src:
    src = src.replace(viejo_calc, nuevo_calc, 1)
    cambios.append('calculo de descuento en $ limitado a maximo 100%')
elif 'Math.min(100, Math.round((valor/subtotal)' in src:
    cambios.append('* calculo ya estaba limitado')

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print()
    for c in cambios:
        print("OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Los errores del servidor ahora se muestran legibles,")
    print("y el descuento en $ ya no puede pasarse de 100%.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
