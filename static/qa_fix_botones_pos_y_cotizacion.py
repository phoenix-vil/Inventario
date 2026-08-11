#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el diseno de botones en 2 lugares:
 1. Punto de Venta: la fila de Descuento + Personalizado quedo METIDA
    dentro de .acciones (por eso se veian chicos, compartiendo el
    espacio de 1 boton entre 2). Se saca a su propia fila arriba,
    cada uno con el mismo tamano que "Dejar en espera" / "Cobrar".
 2. Cotizaciones: el boton "Cobrar en Punto de Venta" usaba la clase
    .tk-btn-sec, que trae flex:1 1 0 pensado para ir en pareja dentro
    de .fila -- al ir solo dentro del contenedor de columna, ese flex
    lo deformaba. Se fuerza flex:none.
Uso: cd ~/inventario-qa/static && python3 qa_fix_botones_pos_y_cotizacion.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

# ============================================================
# 1. pagos.html: sacar la fila de Descuento/Personalizado de .acciones
# ============================================================
PAGOS = os.path.join(STATIC, 'pagos.html')
src = open(PAGOS, encoding='utf-8').read()

viejo = '''  <div class="totales-inner">
    <div class="linea"><span>Subtotal</span><span id="t-subtotal">$0.00</span></div>
    <div class="linea desc" id="linea-desc" style="display:none"><span id="desc-label">Descuento</span><span id="t-desc">-$0.00</span></div>
    <div class="linea linea-ahorro" id="linea-ahorro" style="display:none"><span>🎉 Ahorraste</span><span id="t-ahorro">$0.00</span></div>
    <div class="linea-total"><span>Total</span><span id="t-total">$0.00</span></div>
    <div class="acciones">
      <div style="display:flex;gap:8px;margin-bottom:8px">
        <button class="btn-desc" onclick="abrirDescuento()" style="width:auto;flex:1;margin-bottom:0">% Descuento</button>
        <button onclick="abrirCustomVenta()" style="flex:1;height:44px;border:0.5px dashed var(--border);border-radius:10px;background:transparent;color:var(--text2);font-size:13px;font-weight:600;cursor:pointer">+ Personalizado</button>
      </div>
      <button onclick="dejarEnEspera()" style="width:100%;height:40px;margin-bottom:8px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-size:14px;cursor:pointer">⏸ Dejar en espera</button>
      <button class="btn-cobrar" id="btn-cobrar" onclick="abrirCobro()" disabled>Cobrar</button>
    </div>
  </div>'''
nuevo = '''  <div class="totales-inner">
    <div class="linea"><span>Subtotal</span><span id="t-subtotal">$0.00</span></div>
    <div class="linea desc" id="linea-desc" style="display:none"><span id="desc-label">Descuento</span><span id="t-desc">-$0.00</span></div>
    <div class="linea linea-ahorro" id="linea-ahorro" style="display:none"><span>🎉 Ahorraste</span><span id="t-ahorro">$0.00</span></div>
    <div class="linea-total"><span>Total</span><span id="t-total">$0.00</span></div>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <button class="btn-desc" onclick="abrirDescuento()" style="flex:1;height:48px;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;border:0.5px solid var(--border)">% Descuento</button>
      <button onclick="abrirCustomVenta()" style="flex:1;height:48px;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;border:0.5px solid var(--blue-bg);background:var(--blue-bg);color:var(--blue)">+ Personalizado</button>
    </div>
    <div class="acciones">
      <button onclick="dejarEnEspera()" style="width:100%;height:40px;margin-bottom:8px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-size:14px;cursor:pointer">⏸ Dejar en espera</button>
      <button class="btn-cobrar" id="btn-cobrar" onclick="abrirCobro()" disabled>Cobrar</button>
    </div>
  </div>'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(PAGOS, 'w', encoding='utf-8').write(src)
    res.append("OK pagos.html: Descuento y Personalizado ahora en su propia fila, mismo tamano")
elif 'abrirCustomVenta()" style="flex:1;height:48px' in src:
    res.append("* pagos.html: ya estaba corregido")
else:
    res.append("ERROR pagos.html: no se encontro el bloque de totales-inner exacto")

# ============================================================
# 2. cotizaciones.html: boton "Cobrar en Punto de Venta"
# ============================================================
COT = os.path.join(STATIC, 'cotizaciones.html')
src2 = open(COT, encoding='utf-8').read()

viejo2 = '<button class="tk-btn-sec" onclick="cobrarEnPOS()" style="width:100%">💳 Cobrar en Punto de Venta</button>'
nuevo2 = '<button class="tk-btn-sec" onclick="cobrarEnPOS()" style="width:100%;flex:none">💳 Cobrar en Punto de Venta</button>'
if viejo2 in src2:
    src2 = src2.replace(viejo2, nuevo2, 1)
    open(COT, 'w', encoding='utf-8').write(src2)
    res.append("OK cotizaciones.html: boton Cobrar en Punto de Venta ya no hereda flex:1 1 0")
elif 'flex:none">💳 Cobrar' in src2:
    res.append("* cotizaciones.html: ya estaba corregido")
else:
    res.append("ERROR cotizaciones.html: no se encontro el boton exacto")

print()
for r in res:
    print(r)

ok_total = True
print()
for ruta in [PAGOS, COT]:
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + os.path.basename(ruta) + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 58)
if ok_total and not any(r.startswith('ERROR') for r in res):
    print("Ambos son cambios de HTML/CSS, no requieren reiniciar el servicio.")
    print("Prueba con Ctrl+Shift+R.")
else:
    print("Revisa los mensajes de arriba antes de probar.")
