#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Fuerza a negro los textos de color en la impresion termica.
La XP-58 es monocromatica: el verde de "Ahorraste" y el rojo de
"Descuento" salian en gris muy tenue o no salian. Se pasan a negro
y en negrita para que se distingan igual.
Uso: cd ~/inventario-qa/static && python3 qa_impresion_colores.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

REGLA = ("img{max-width:34mm;height:auto}"
         ".tk-desc,.tk-ahorro,.tk-line span,.tk-total,.tk-sub,.tk-foot{color:#000 !important}"
         ".tk-desc,.tk-ahorro{font-weight:bold}")

viejo = "img{max-width:34mm;height:auto}"

for nombre in ['pagos.html', 'historial.html', 'devoluciones.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    if '.tk-desc,.tk-ahorro,.tk-line span' in src:
        res.append("* " + nombre + ": ya estaba corregido")
        continue
    n = src.count(viejo)
    if n >= 1:
        src = src.replace(viejo, REGLA, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        res.append("OK " + nombre + ": colores forzados a negro en impresion")
    else:
        res.append("ERROR " + nombre + ": no se encontro la regla img del estilo de impresion")

print()
for r in res:
    print(r)

ok_total = True
print()
for nombre in ['pagos.html', 'historial.html', 'devoluciones.html']:
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
    print("Listo. Imprime un ticket con descuento para comprobar.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
