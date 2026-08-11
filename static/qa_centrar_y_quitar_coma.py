#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Refuerza el centrado de .tk-sub (Sucursal/Ticket/fecha/Operador)
con text-align:center explicito, en vez de depender de la herencia.
2. Quita la coma entre fecha y hora (usa espacio en vez de coma).
Aplica a pagos.html, historial.html y clientes.html.
Uso: cd ~/inventario-qa/static && python3 qa_centrar_y_quitar_coma.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo_css = '.tk-sub{font-size:12px;color:var(--text)}'
nuevo_css = '.tk-sub{font-size:12px;color:var(--text);text-align:center}'

viejo_css_clientes = '.tk-sub{font-size:12px;color:#000}'
nuevo_css_clientes = '.tk-sub{font-size:12px;color:#000;text-align:center}'

viejo_fecha = "new Date(v.fecha).toLocaleString('es-MX')"
nuevo_fecha = "new Date(v.fecha).toLocaleString('es-MX').replace(',', '')"

viejo_fecha_datos = "new Date(datos.fecha).toLocaleString('es-MX')"
nuevo_fecha_datos = "new Date(datos.fecha).toLocaleString('es-MX').replace(',', '')"

for nombre in ['pagos.html', 'historial.html', 'clientes.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    original = src
    cambios = []

    if viejo_css in src:
        n = src.count(viejo_css)
        src = src.replace(viejo_css, nuevo_css)
        cambios.append('centrado reforzado en .tk-sub (' + str(n) + ' ocurrencia(s))')
    elif 'text-align:center}' in src and '.tk-sub{' in src:
        cambios.append('* .tk-sub ya tenia centrado')

    if viejo_css_clientes in src:
        n = src.count(viejo_css_clientes)
        src = src.replace(viejo_css_clientes, nuevo_css_clientes)
        cambios.append('centrado reforzado en .tk-sub de clientes (' + str(n) + ' ocurrencia(s))')

    n_fecha = src.count(viejo_fecha)
    if n_fecha > 0:
        src = src.replace(viejo_fecha, nuevo_fecha)
        cambios.append('coma quitada de fecha (v.fecha, ' + str(n_fecha) + ' ocurrencia(s))')

    n_fecha_datos = src.count(viejo_fecha_datos)
    if n_fecha_datos > 0:
        src = src.replace(viejo_fecha_datos, nuevo_fecha_datos)
        cambios.append('coma quitada de fecha (datos.fecha, ' + str(n_fecha_datos) + ' ocurrencia(s))')

    if cambios:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios:
            print("OK " + nombre + ": " + c)
    else:
        print("* " + nombre + ": sin cambios pendientes")
    print()

ok_total = True
for nombre in ['pagos.html', 'historial.html', 'clientes.html']:
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
    print("Listo. Fecha sin coma (ej: '31/7/2026 1:43 p.m.') y texto")
    print("debajo del logo centrado de forma explicita.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
