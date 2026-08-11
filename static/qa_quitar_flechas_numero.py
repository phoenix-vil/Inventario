#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Quita las flechitas de subir/bajar de TODOS los campos numericos
de la app, agregando la regla al CSS compartido (modern.css).
Uso: cd ~/inventario-qa/static && python3 qa_quitar_flechas_numero.py
"""
import os

STATIC = os.path.expanduser('~/inventario-qa/static')
MODERN = os.path.join(STATIC, 'modern.css')
src = open(MODERN, encoding='utf-8').read()

if 'webkit-inner-spin-button' in src:
    print("* La regla ya existia, se omite")
else:
    regla = '''

/* Quitar las flechas de subir/bajar de los campos numericos en toda la app */
input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button{
  -webkit-appearance:none;
  margin:0;
}
input[type=number]{
  -moz-appearance:textfield;
}
'''
    src = src.rstrip('\n') + regla
    open(MODERN, 'w', encoding='utf-8').write(src)
    print("OK: regla agregada a modern.css")

print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. Los campos numericos ya no deberian mostrar las flechitas")
print("en ninguna pantalla de la app (Punto de venta, Gastos, Usuarios, etc.)")
