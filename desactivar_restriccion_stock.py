#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desactiva la restriccion que impide vender productos con stock 0 (o insuficiente).
Tambien permite que el stock quede en negativo sin que la API se caiga
(se quita la validacion ge=0 que antes rechazaba stock negativo en las respuestas).

Uso: cd ~/inventario && python3 desactivar_restriccion_stock.py
"""
import os, re, ast

BASE = os.path.expanduser('~/inventario')

cambios_ok = []
cambios_no = []

# ================================================================
# 1. schemas.py: permitir stock negativo (sin esto, la API se cae
#    en cuanto una venta deje el stock en negativo)
# ================================================================
print("1. Actualizando schemas.py...")
schemas_path = os.path.join(BASE, 'schemas.py')
src = open(schemas_path, encoding='utf-8').read()
original = src

reemplazos_schemas = [
    ('stock: float = Field(default=0, ge=0)', 'stock: float = Field(default=0)'),
    ('stock: Optional[float] = Field(None, ge=0)', 'stock: Optional[float] = Field(None)'),
]
for viejo, nuevo in reemplazos_schemas:
    if viejo in src:
        src = src.replace(viejo, nuevo)
        cambios_ok.append('schemas.py: ' + viejo)
    else:
        cambios_no.append('schemas.py: no encontrado -> ' + viejo)

if src != original:
    open(schemas_path, 'w', encoding='utf-8').write(src)

# ================================================================
# 2. main.py: quitar el bloqueo de "stock insuficiente" al vender
# ================================================================
print("2. Actualizando main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()
original = src

patron_bloqueo = re.compile(
    r'[ \t]*if p\.stock < item\.cantidad:\s*\n'
    r'[ \t]*raise HTTPException\(\s*\n'
    r'[ \t]*status_code=400,\s*\n'
    r'[ \t]*detail=f"Stock insuficiente[^\n]*\n'
    r'[ \t]*\)\s*\n'
)

nueva_src, n = patron_bloqueo.subn(
    '        # Restriccion de stock desactivada: se permite vender con stock 0 o negativo\n',
    src, count=1
)
if n:
    src = nueva_src
    cambios_ok.append('main.py: bloqueo de stock insuficiente eliminado de registrar_venta')
else:
    cambios_no.append('main.py: no se encontro el bloque exacto del bloqueo de stock')

if src != original:
    open(main_path, 'w', encoding='utf-8').write(src)

# Verificar sintaxis de main.py ANTES de continuar
print("   Verificando sintaxis de main.py...")
try:
    ast.parse(open(main_path, encoding='utf-8').read())
    print("   OK sintaxis valida")
    main_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    main_ok = False

# ================================================================
# 3. pagos.html: quitar el tope de cantidad maxima segun stock
# ================================================================
print("3. Actualizando static/pagos.html...")
pagos_path = os.path.join(BASE, 'static', 'pagos.html')
src = open(pagos_path, encoding='utf-8').read()
original = src

patron_tope = re.compile(
    r"if\(c\.stock!=null && val>c\.stock\)\{\s*"
    r"const disp=c\.vendido_por_peso\?c\.stock\.toFixed\(3\)\+' kg':c\.stock;\s*"
    r"alert\(`[^`]*`\);\s*"
    r"val=c\.stock;\s*"
    r"\}"
)

nueva_src, n = patron_tope.subn(
    "// Restriccion de stock maximo desactivada: se permite vender aunque no haya stock",
    src, count=1
)
if n:
    src = nueva_src
    cambios_ok.append('pagos.html: tope de cantidad maxima segun stock eliminado')
else:
    cambios_no.append('pagos.html: no se encontro el bloque exacto del tope de stock')

if src != original:
    open(pagos_path, 'w', encoding='utf-8').write(src)

# Verificar balance de llaves en pagos.html
scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
pagos_ok = True
for s in scripts:
    if s.count('{') != s.count('}'):
        pagos_ok = False

# ================================================================
# Resumen
# ================================================================
print()
print("=" * 55)
print("CAMBIOS APLICADOS:")
for c in cambios_ok:
    print("  OK  " + c)
print()
if cambios_no:
    print("NO SE ENCONTRARON (revisar manualmente):")
    for c in cambios_no:
        print("  !!  " + c)
    print()

if main_ok and pagos_ok:
    print("Verificaciones de sintaxis OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print()
    print("Listo. Ya puedes vender productos aunque su stock este en 0.")
    print("El stock puede quedar en negativo tras la venta sin que la app se caiga.")
else:
    print("ADVERTENCIA: no se reinicio el servicio por un problema de sintaxis.")
    print("Revisa los mensajes de arriba antes de reiniciar manualmente.")
