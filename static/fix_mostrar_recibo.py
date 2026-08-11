#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige el enganche: confirmarAbono() debe llamar a mostrarRecibo(data)
tras un abono exitoso. Usa un ancla sin acentos para evitar problemas
de codificacion.
Uso: cd ~/inventario/static && python3 fix_mostrar_recibo.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src

if 'mostrarRecibo(data);' in src:
    print("* mostrarRecibo(data) ya se estaba llamando, no se hace nada")
else:
    viejo = "abrirDetalle(clienteActualId);\n    cargarClientes();\n  }catch(e){"
    nuevo = "abrirDetalle(clienteActualId);\n    cargarClientes();\n    mostrarRecibo(data);\n  }catch(e){"

    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        print("OK: mostrarRecibo(data) agregado despues de cargarClientes()")
    else:
        print("ERROR: coincidencias inesperadas (" + str(n) + "). Revisar manualmente.")

if src != original:
    open(CLIENTES, 'w', encoding='utf-8').write(src)
    print("Archivo guardado.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Registra un abono de prueba: ahora si debe aparecer el recibo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
