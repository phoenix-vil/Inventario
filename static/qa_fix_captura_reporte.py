#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el recorte del reporte: html2canvas no capturaba el ancho
completo del contenedor colocado a -9999px. Se le pasa width/windowWidth
explicitos y se posiciona el contenedor dentro del viewport pero
invisible (opacity casi 0, z-index negativo).
Uso: cd ~/inventario-qa/static && python3 qa_fix_captura_reporte.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo_pos = """  cont.style.position='absolute'; cont.style.left='-9999px'; cont.style.top='0';"""
nuevo_pos = """  cont.style.position='fixed'; cont.style.left='0'; cont.style.top='0'; cont.style.zIndex='-1000'; cont.style.opacity='0.01'; cont.style.pointerEvents='none';"""

viejo_cap = """    const canvas = await html2canvas(cont, {scale:2, backgroundColor:'#ffffff', useCORS:true});"""
nuevo_cap = """    const canvas = await html2canvas(cont, {scale:2, backgroundColor:'#ffffff', useCORS:true, width:595, windowWidth:595, scrollX:0, scrollY:0});"""

for nombre in ['historial.html', 'dashboard.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    original = src
    cambios = []

    if viejo_pos in src:
        n = src.count(viejo_pos)
        src = src.replace(viejo_pos, nuevo_pos)
        cambios.append('posicion del contenedor corregida (' + str(n) + ')')
    elif "cont.style.zIndex='-1000'" in src:
        cambios.append('* posicion ya estaba corregida')

    if viejo_cap in src:
        src = src.replace(viejo_cap, nuevo_cap)
        cambios.append('captura con ancho explicito')
    elif 'windowWidth:595' in src:
        cambios.append('* captura ya tenia ancho explicito')

    if src != original:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios:
            print("OK " + nombre + ": " + c)
    else:
        for c in cambios:
            print(nombre + ": " + c)
        if not cambios:
            print("ERROR " + nombre + ": no se encontraron los patrones")

print()
ok_total = True
for nombre in ['historial.html', 'dashboard.html']:
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
    print("Listo. Genera el reporte de nuevo con Ctrl+Shift+R.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
