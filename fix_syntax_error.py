#!/usr/bin/env python3
import os, re, ast

MAIN = os.path.expanduser('~/inventario/main.py')
src = open(MAIN, encoding='utf-8').read()
original = src

src = re.sub(r',(\s*),(\s*TrasladoStock\s*\))', r',\2', src)

if src != original:
    open(MAIN, 'w', encoding='utf-8').write(src)
    print("Coma duplicada eliminada del import")
else:
    print("No se encontro el patron exacto del bug. Mostrando linea 19 actual:")
    lineas = src.splitlines()
    for i in range(max(0, 19-4), min(len(lineas), 19+3)):
        marca = ">>> " if i == 18 else "    "
        print(marca + str(i+1) + ": " + lineas[i])

print("")
print("Verificando sintaxis...")
try:
    ast.parse(open(MAIN, encoding='utf-8').read())
    print("main.py ahora tiene sintaxis valida")
    print("")
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    import time
    time.sleep(2)
    os.system("sudo systemctl is-active inventario")
except SyntaxError as e:
    print("TODAVIA hay un error de sintaxis:")
    print("Linea " + str(e.lineno) + ": " + str(e.text))
    print(e.msg)
    print("")
    print("Copia y comparte este error para corregirlo.")
