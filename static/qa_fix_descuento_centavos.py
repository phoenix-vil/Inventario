#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el descuento en pesos que descontaba 1 centavo de mas.
Causa: el monto se convertia a porcentaje redondeado a 2 decimales,
y el servidor recalculaba el total desde ese porcentaje truncado.
  Ej: $350 con $50 de descuento -> 14.2857% se volvia 14.29%
      -> total $299.99 en vez de $300.00 (descuento real $50.01)
Solucion: se conserva el porcentaje con precision completa para el
calculo, y se redondea unicamente al mostrarlo en pantalla y ticket.
Uso: cd ~/inventario-qa/static && python3 qa_fix_descuento_centavos.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

# ============================================================
# 1. pagos.html: no redondear el porcentaje calculado
# ============================================================
ruta = os.path.join(STATIC, 'pagos.html')
src = open(ruta, encoding='utf-8').read()

viejo = "    pct = Math.min(100, Math.round((valor/subtotal)*10000)/100);"
nuevo = "    pct = Math.min(100, (valor/subtotal)*100);"
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK pagos.html: el descuento en $ conserva precision completa")
elif "pct = Math.min(100, (valor/subtotal)*100);" in src:
    res.append("* pagos.html: ya conservaba la precision")
else:
    res.append("ERROR pagos.html: no se encontro el calculo del porcentaje")

# --- helper para mostrar el porcentaje redondeado ---
if 'function fmtPct' not in src:
    helper = "function fmtPct(p){const n=Math.round((Number(p)||0)*100)/100;return (n%1===0)?String(n):n.toFixed(2).replace(/0$/,'');}\n"
    m = re.search(r"function money\([^\)]*\)\{[^\n]*\n", src)
    if m:
        src = src[:m.end()] + helper + src[m.end():]
        res.append("OK pagos.html: helper fmtPct agregado")
    else:
        res.append("ADVERTENCIA pagos.html: no se encontro money() para insertar fmtPct")

# --- usar fmtPct en el ticket y en el carrito ---
n1 = src.count('${v.descuento_extra_pct}%')
if n1:
    src = src.replace('${v.descuento_extra_pct}%', '${fmtPct(v.descuento_extra_pct)}%')
    res.append("OK pagos.html: ticket muestra el porcentaje redondeado (" + str(n1) + ")")

n2 = src.count('`Descuento ${descuentoExtra}%')
if n2:
    src = src.replace('`Descuento ${descuentoExtra}%', '`Descuento ${fmtPct(descuentoExtra)}%')
    res.append("OK pagos.html: carrito muestra el porcentaje redondeado (" + str(n2) + ")")

open(ruta, 'w', encoding='utf-8').write(src)

# ============================================================
# 2. historial.html: mismo formato en el ticket
# ============================================================
ruta = os.path.join(STATIC, 'historial.html')
src = open(ruta, encoding='utf-8').read()

if 'function fmtPct' not in src:
    helper = "function fmtPct(p){const n=Math.round((Number(p)||0)*100)/100;return (n%1===0)?String(n):n.toFixed(2).replace(/0$/,'');}\n"
    m = re.search(r"function money\([^\)]*\)\{[^\n]*\n", src)
    if m:
        src = src[:m.end()] + helper + src[m.end():]
        res.append("OK historial.html: helper fmtPct agregado")
    else:
        res.append("ADVERTENCIA historial.html: no se encontro money() para insertar fmtPct")

n3 = src.count('${v.descuento_extra_pct}%')
if n3:
    src = src.replace('${v.descuento_extra_pct}%', '${fmtPct(v.descuento_extra_pct)}%')
    res.append("OK historial.html: ticket muestra el porcentaje redondeado (" + str(n3) + ")")

open(ruta, 'w', encoding='utf-8').write(src)

# ============================================================
print()
for r in res:
    print(r)

ok_total = True
print()
for nombre in ['pagos.html', 'historial.html']:
    s = open(os.path.join(STATIC, nombre), encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 58)
if ok_total and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. PRUEBA ESTE CASO EXACTO:")
    print("  Carrito de $350 -> descuento en $ de 50 -> el total debe")
    print("  quedar en $300.00 exactos (antes daba $299.99)")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
