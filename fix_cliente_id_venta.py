#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige el bug: cliente_id nunca se agrego realmente a la clase Venta
en database.py (el patch anterior no encontro el patron exacto).
Uso: cd ~/inventario && python3 fix_cliente_id_venta.py
"""
import os, ast

BASE = os.path.expanduser('~/inventario')
db_path = os.path.join(BASE, 'database.py')
src = open(db_path, encoding='utf-8').read()
original = src

viejo = '''    tpv_terminal = Column(String, nullable=True)
    detalle_json = Column(String, nullable=False)
    pago_con = Column(Float, nullable=True)
    cambio = Column(Float, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sucursal(Base):'''

nuevo = '''    tpv_terminal = Column(String, nullable=True)
    detalle_json = Column(String, nullable=False)
    pago_con = Column(Float, nullable=True)
    cambio = Column(Float, nullable=True)
    cliente_id = Column(Integer, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sucursal(Base):'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("OK: cliente_id agregado a la clase Venta")
elif 'cliente_id = Column(Integer, nullable=True)' in src:
    print("* cliente_id ya existia en algun lado, revisando si quedo en Venta...")
    # Verificar especificamente dentro del bloque de Venta
    import re
    m = re.search(r'class Venta\(Base\):.*?(?=\n\nclass )', src, re.DOTALL)
    if m and 'cliente_id' in m.group(0):
        print("  Confirmado: cliente_id SI esta en la clase Venta. No se requiere cambio.")
    else:
        print("  ADVERTENCIA: cliente_id existe en otra clase pero NO en Venta. Revisar manualmente.")
else:
    print("ERROR: no se encontro el patron exacto. No se modifico nada.")
    print("Comparte el resultado de: grep -n 'class Venta' -A 20 database.py")

if src != original:
    open(db_path, 'w', encoding='utf-8').write(src)
    print("Archivo guardado.")

try:
    ast.parse(open(db_path, encoding='utf-8').read())
    print("Sintaxis de database.py: OK")
    ok = True
except SyntaxError as e:
    print("ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    ok = False

print()
if ok:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Prueba de nuevo: crear cliente y vender a credito.")
else:
    print("ADVERTENCIA: no se reinicio el servicio por el error de arriba.")
