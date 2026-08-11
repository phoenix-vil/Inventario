#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Ajuste fino final: pie de pagina identico (negro, con exclamaciones,
sin cursiva) y espaciado mas ajustado alrededor de las lineas.
Uso: cd ~/inventario-qa/static && python3 qa_pdf_ajuste_fino.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()

    inicio = src.find('async function generarPDFTicketVenta(v){')
    if inicio == -1:
        print("ERROR " + nombre + ": no se encontro la funcion")
        continue

    profundidad = 0
    encontrado = False
    fin = -1
    for idx in range(inicio, len(src)):
        c = src[idx]
        if c == '{':
            profundidad += 1
            encontrado = True
        elif c == '}':
            profundidad -= 1
            if encontrado and profundidad == 0:
                fin = idx + 1
                break

    if fin == -1:
        print("ERROR " + nombre + ": no se pudo determinar el cierre")
        continue

    f = src[inicio:fin]
    cambios_aqui = []

    # 1. Pie de pagina: negro, con exclamaciones, sin cursiva
    viejo_pie = "  doc.setFont('courier','italic'); doc.setFontSize(9); doc.setTextColor(90);\n  doc.text('Gracias por su compra', centerX, y, {align:'center'});"
    nuevo_pie = "  doc.setFont('courier','normal'); doc.setFontSize(9); doc.setTextColor(0);\n  doc.text('¡Gracias por su compra!', centerX, y, {align:'center'});"
    if viejo_pie in f:
        f = f.replace(viejo_pie, nuevo_pie, 1)
        cambios_aqui.append('pie de pagina (negro, con exclamaciones)')

    # 2. Espaciado mas ajustado: reducir los +8/+6/+4 antes de las lineas
    #    y los +16/+18 despues de ellas, para que quede mas compacto
    ajustes_espaciado = [
        ('y+=8;\n  lineaPunteada(y); y+=16;', 'y+=4;\n  lineaPunteada(y); y+=10;'),
        ('y+=4;\n  lineaPunteada(y); y+=18;', 'y+=2;\n  lineaPunteada(y); y+=10;'),
        ('  lineaPunteada(y); y+=18;\n\n  doc.setFont', '  lineaPunteada(y); y+=10;\n\n  doc.setFont'),
    ]
    for viejo_e, nuevo_e in ajustes_espaciado:
        if viejo_e in f:
            f = f.replace(viejo_e, nuevo_e)
            cambios_aqui.append('espaciado reducido')

    if cambios_aqui:
        src = src[:inicio] + f + src[fin:]
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": " + ", ".join(set(cambios_aqui)))
        total += 1
    else:
        print("* " + nombre + ": no se encontraron los patrones esperados (puede ya estar ajustado)")

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
    print("Listo. Pie de pagina igualado y espaciado mas compacto.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
