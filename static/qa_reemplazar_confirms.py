#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Reemplaza los confirm() nativos de "eliminar" en Clientes, Gastos,
Usuarios y Sucursales por el modal centralizado de auth.js.
Uso: cd ~/inventario-qa/static && python3 qa_reemplazar_confirms.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

reemplazos = {
    'clientes.html': [
        (
            "if(!confirm('¿Eliminar a ' + nombre + '? Esta acción no se puede deshacer.\\n\\nSolo se puede eliminar si no tiene saldo pendiente.')) return;",
            "if(!(await confirmarPersonalizado('¿Eliminar a ' + nombre + '?\\n\\nSolo se puede eliminar si no tiene saldo pendiente.', 'Eliminar cliente'))) return;"
        ),
    ],
    'gastos.html': [
        (
            "if(!confirm('¿Eliminar este gasto? Esta acción no se puede deshacer.')) return;",
            "if(!(await confirmarPersonalizado('¿Eliminar este gasto? Esta acción no se puede deshacer.', 'Eliminar gasto'))) return;"
        ),
    ],
    'usuarios.html': [
        (
            'if(!confirm(`¿Eliminar al usuario "${usuario}"? Esta acción no se puede deshacer.`))return;',
            "if(!(await confirmarPersonalizado(`¿Eliminar al usuario \"${usuario}\"? Esta acción no se puede deshacer.`, 'Eliminar usuario')))return;"
        ),
    ],
    'sucursales.html': [
        (
            'if(!confirm(`¿Eliminar la sucursal "${nombre}"?`))return;',
            "if(!(await confirmarPersonalizado(`¿Eliminar la sucursal \"${nombre}\"?`, 'Eliminar sucursal')))return;"
        ),
    ],
}

for nombre, pares in reemplazos.items():
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    original = src
    cambios = []
    for viejo, nuevo in pares:
        if viejo in src:
            src = src.replace(viejo, nuevo, 1)
            cambios.append('confirm() reemplazado')
        elif 'confirmarPersonalizado(' in src:
            cambios.append('* ya estaba reemplazado')
        else:
            print("ERROR " + nombre + ": no se encontro el texto exacto")

    if src != original:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios:
            print("OK " + nombre + ": " + c)
    else:
        for c in cambios:
            print(nombre + ": " + c)

print()
ok_total = True
for nombre in reemplazos.keys():
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
    print("Listo. Los 4 confirm() de eliminar ahora usan el modal propio.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
