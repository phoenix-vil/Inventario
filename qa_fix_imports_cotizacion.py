#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega los imports faltantes de Cotizacion (database.py) y
RegistrarCotizacion (schemas.py), que se crearon en sus archivos pero
nunca se importaron en main.py -- causaba NameError al arrancar.
Uso: cd ~/inventario-qa && python3 qa_fix_imports_cotizacion.py
"""
import os

MAIN = os.path.expanduser('~/inventario-qa/main.py')
src = open(MAIN, encoding='utf-8').read()
res = []

# --- database.py: Cotizacion ---
viejo_db = "from database import VentaPendiente"
nuevo_db = "from database import VentaPendiente\nfrom database import Cotizacion"
if viejo_db in src and "from database import Cotizacion" not in src:
    src = src.replace(viejo_db, nuevo_db, 1)
    res.append("OK: import de Cotizacion (database.py) agregado")
elif "from database import Cotizacion" in src:
    res.append("* el import de Cotizacion ya estaba")
else:
    res.append("ERROR: no se encontro 'from database import VentaPendiente'")

# --- schemas.py: RegistrarCotizacion ---
viejo_sc = "from schemas import CrearVentaPendiente"
nuevo_sc = "from schemas import CrearVentaPendiente\nfrom schemas import RegistrarCotizacion"
if viejo_sc in src and "from schemas import RegistrarCotizacion" not in src:
    src = src.replace(viejo_sc, nuevo_sc, 1)
    res.append("OK: import de RegistrarCotizacion (schemas.py) agregado")
elif "from schemas import RegistrarCotizacion" in src:
    res.append("* el import de RegistrarCotizacion ya estaba")
else:
    res.append("ERROR: no se encontro 'from schemas import CrearVentaPendiente'")

open(MAIN, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

print()
try:
    compile(open(MAIN, encoding='utf-8').read(), MAIN, 'exec')
    print("main.py: sintaxis Python OK")
    sintaxis_ok = True
except SyntaxError as e:
    print("ERROR de sintaxis, linea", e.lineno, ":", e.msg)
    sintaxis_ok = False

print()
print("=" * 58)
if sintaxis_ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print()
    import time
    time.sleep(1.5)
    os.system("sudo systemctl status inventario-qa --no-pager | head -6")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
