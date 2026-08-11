#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega "Credito" y "Transferencia" como opciones del filtro de
metodo de pago en Historial (solo tenia Efectivo y Tarjeta).
Uso: cd ~/inventario-qa/static && python3 qa_fix_filtro_metodo_pago.py
"""
import os, re

HISTORIAL = os.path.expanduser('~/inventario-qa/static/historial.html')
src = open(HISTORIAL, encoding='utf-8').read()

viejo = '''      <select id="f-metodo">
        <option value="">Todos</option>
        <option value="efectivo">Efectivo</option>
        <option value="tarjeta">Tarjeta</option>
      </select>'''

nuevo = '''      <select id="f-metodo">
        <option value="">Todos</option>
        <option value="efectivo">Efectivo</option>
        <option value="tarjeta">Tarjeta</option>
        <option value="credito">Crédito</option>
        <option value="transferencia">Transferencia</option>
      </select>'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    open(HISTORIAL, 'w', encoding='utf-8').write(src)
    print("OK: opciones 'Credito' y 'Transferencia' agregadas al filtro")
elif 'value="credito">Crédito</option>' in src:
    print("* Ya estaba corregido")
else:
    print("ERROR: no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El filtro de Historial ya tiene las 4 opciones.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
