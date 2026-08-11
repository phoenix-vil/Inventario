#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Corrige el texto claro: el contenedor del PDF hereda las
variables de color del modo oscuro del sistema si esta activo, aunque
el fondo sea blanco. Se fuerzan las variables a sus valores de modo
claro dentro del contenedor.
2. Agrega el monto ahorrado junto al porcentaje en cada producto con
descuento individual.
Uso: cd ~/inventario-qa/static && python3 qa_fix_colores_y_monto.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

VARS_MODO_CLARO = (
    "--bg:#f5f4f0;--bg2:#fff;--border:#e2e0d8;--text:#1a1a18;--text2:#6b6b66;"
    "--blue:#185fa5;--blue-bg:#e6f1fb;--green:#3b6d11;--green-bg:#eaf3de;"
    "--amber:#854f0b;--amber-bg:#faeeda;--red:#a32d2d;--red-bg:#fcebeb;"
)

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    cambios_aqui = []

    # ---- 1. Forzar variables de modo claro en el contenedor del screenshot ----
    viejo_contenedor = "contenedor.style.color = '#000000';"
    nuevo_contenedor = "contenedor.style.color = '#000000';\n  contenedor.setAttribute('style', contenedor.getAttribute('style') + ';" + VARS_MODO_CLARO + "');"
    if viejo_contenedor in src and 'VARS_MODO_CLARO' not in src:
        # Evitar aplicar dos veces buscando una marca unica
        if "--bg:#f5f4f0;--bg2:#fff" not in src:
            src = src.replace(viejo_contenedor, nuevo_contenedor, 1)
            cambios_aqui.append('variables de color forzadas a modo claro')

    # ---- 2. Agregar el monto ahorrado junto al porcentaje ----
    viejo_badge = '''    const badgeDesc = tieneDescItem
      ? ` <span style="color:#a32d2d;font-weight:600">(-${Math.round((1-it.precio_unitario/it.precio_original)*100)}%)</span>`
      : '';'''
    nuevo_badge = '''    const badgeDesc = tieneDescItem
      ? ` <span style="color:#a32d2d;font-weight:600">(-${Math.round((1-it.precio_unitario/it.precio_original)*100)}%, -${money(it.ahorro)})</span>`
      : '';'''
    if viejo_badge in src:
        src = src.replace(viejo_badge, nuevo_badge, 1)
        cambios_aqui.append('monto ahorrado agregado junto al porcentaje')
    elif '-${money(it.ahorro)}' in src:
        cambios_aqui.append('* monto ya estaba agregado')

    if cambios_aqui:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios_aqui:
            print("OK " + nombre + ": " + c)
        total += 1
    else:
        print("ERROR " + nombre + ": no se encontraron los patrones esperados")

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
    print("Listo. El texto ya no deberia depender del modo oscuro del sistema,")
    print("y cada producto con descuento muestra el % y el monto ahorrado.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
