#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el filtro de metodo_pago en listar_ventas: solo reconocia
"efectivo"/"tarjeta", ignorando "credito"/"transferencia" (por lo que
el filtro no se aplicaba y mostraba todas las ventas sin filtrar).
Uso: cd ~/inventario-qa && python3 static/qa_fix_filtro_backend.py
"""
import os

MAIN = os.path.expanduser('~/inventario-qa/main.py')
src = open(MAIN, encoding='utf-8').read()

viejo = '''    if metodo_pago in ("efectivo", "tarjeta"):
        query = query.filter(Venta.metodo_pago == metodo_pago)'''

nuevo = '''    if metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia"):
        query = query.filter(Venta.metodo_pago == metodo_pago)'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    open(MAIN, 'w', encoding='utf-8').write(src)
    print("OK: filtro corregido para reconocer los 4 metodos de pago")
elif '"credito", "transferencia")' in src:
    print("* Ya estaba corregido")
else:
    print("ERROR: no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. El filtro de Historial ahora deberia funcionar con los 4 metodos.")
