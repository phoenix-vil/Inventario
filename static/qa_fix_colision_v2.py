#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Version robusta: quita el bloque JS duplicado localizandolo por
su inicio conocido y contando llaves para encontrar el final real,
en vez de comparar un bloque de texto completo (propenso a fallar).
Uso: cd ~/inventario-qa/static && python3 qa_fix_colision_v2.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

inicio = src.find("let _resolverConfirmarGenerico = null;")
if inicio == -1:
    print("* No se encontro 'let _resolverConfirmarGenerico = null;' -- puede que ya se haya quitado")
else:
    # Buscar el final de la ULTIMA funcion del bloque (confirmarPersonalizado),
    # que es la que viene despues de este punto. Localizamos su apertura
    # y contamos llaves desde ahi para encontrar su cierre real.
    idx_func_final = src.find('function confirmarPersonalizado(mensaje, titulo){', inicio)
    if idx_func_final == -1:
        print("ERROR: no se encontro 'function confirmarPersonalizado' despues del inicio")
    else:
        profundidad = 0
        encontrado = False
        fin = -1
        for idx in range(idx_func_final, len(src)):
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
            print("ERROR: no se pudo determinar el cierre de confirmarPersonalizado")
        else:
            bloque_a_quitar = src[inicio:fin]
            print("Bloque identificado para eliminar (primeras 100 caracteres):")
            print("  " + bloque_a_quitar[:100].replace('\n', ' | '))
            print("Bloque identificado (ultimos 60 caracteres):")
            print("  " + bloque_a_quitar[-60:].replace('\n', ' | '))
            src = src[:inicio] + src[fin:]
            open(PAGOS, 'w', encoding='utf-8').write(src)
            print()
            print("OK: bloque JS duplicado eliminado (" + str(len(bloque_a_quitar)) + " caracteres)")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Prueba Punto de Venta de nuevo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
    print("Comparte esta salida completa para revisar.")
