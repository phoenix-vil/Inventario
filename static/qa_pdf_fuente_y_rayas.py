#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Ajusta el PDF para que sea casi identico a Imprimir:
- Fuente Courier (monoespaciada) en vez de Helvetica
- Rayitas largas en vez de puntos en las lineas separadoras
Uso: cd ~/inventario-qa/static && python3 qa_pdf_fuente_y_rayas.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    original = src

    inicio = src.find('async function generarPDFTicketVenta(v){')
    if inicio == -1:
        print("ERROR " + nombre + ": no se encontro generarPDFTicketVenta")
        continue

    profundidad = 0
    encontrado_inicio_llave = False
    fin = -1
    for idx in range(inicio, len(src)):
        c = src[idx]
        if c == '{':
            profundidad += 1
            encontrado_inicio_llave = True
        elif c == '}':
            profundidad -= 1
            if encontrado_inicio_llave and profundidad == 0:
                fin = idx + 1
                break

    if fin == -1:
        print("ERROR " + nombre + ": no se pudo determinar el cierre de la funcion")
        continue

    funcion_actual = src[inicio:fin]

    if "lineaPunteada" not in funcion_actual:
        print("ERROR " + nombre + ": la funcion no tiene lineaPunteada, esperaba la version v2")
        continue

    funcion_nueva = funcion_actual
    # 1. Cambiar helvetica -> courier
    funcion_nueva = funcion_nueva.replace("'helvetica'", "'courier'")
    # 2. Rayitas mas largas en vez de puntos
    funcion_nueva = funcion_nueva.replace(
        "doc.setLineDashPattern([2, 1.5], 0);",
        "doc.setLineDashPattern([4, 2.5], 0);"
    )

    if funcion_nueva == funcion_actual:
        print("* " + nombre + ": no hubo cambios que aplicar (ya estaba igual)")
        continue

    src = src[:inicio] + funcion_nueva + src[fin:]
    open(ruta, 'w', encoding='utf-8').write(src)
    print("OK " + nombre + ": fuente Courier + rayitas largas aplicadas")
    total += 1

print()
print("Total actualizado: " + str(total))
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
    print("Listo. El PDF ahora usa fuente Courier y rayitas largas,")
    print("deberia verse casi identico a Imprimir.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
