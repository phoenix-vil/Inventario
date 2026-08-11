#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Tres correcciones en devoluciones:
 1. DINERO: se devolvia precio_unitario sin aplicar el descuento general
    del carrito (descuento_extra_pct), devolviendo de mas.
 2. Bloquea devolver sobre una venta ya devuelta por completo.
 3. El detalle de venta ahora expone, por articulo, cuanto se devolvio
    ya y cuanto queda disponible (para que la pantalla lo muestre).
Uso: cd ~/inventario-qa && python3 qa_fix_devolucion_descuentos.py
"""
import os, re

MAIN = os.path.expanduser('~/inventario-qa/main.py')
src = open(MAIN, encoding='utf-8').read()
res = []

# ============================================================
# 1. Aplicar el descuento general al importe devuelto (devolucion)
# ============================================================
viejo = '''        importe = round(linea.get("precio_unitario", 0) * cant, 2)
        monto_total += importe
        detalle_dev.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": -cant,'''
nuevo = '''        factor_desc = 1 - (v.descuento_extra_pct or 0) / 100
        importe = round(linea.get("precio_unitario", 0) * cant * factor_desc, 2)
        monto_total += importe
        detalle_dev.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": -cant,'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK devolucion: ahora aplica el descuento general del carrito")
elif 'factor_desc = 1 - (v.descuento_extra_pct or 0) / 100' in src:
    res.append("* devolucion: ya aplicaba el descuento general")
else:
    res.append("ERROR: no se encontro el calculo de importe en devolver_items")

# ============================================================
# 2. Mismo ajuste en cancelar_venta
# ============================================================
viejo2 = '''        importe = round(linea.get("precio_unitario", 0) * pendiente, 2)
        monto_total += importe'''
nuevo2 = '''        factor_desc = 1 - (v.descuento_extra_pct or 0) / 100
        importe = round(linea.get("precio_unitario", 0) * pendiente * factor_desc, 2)
        monto_total += importe'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    res.append("OK cancelacion: ahora aplica el descuento general del carrito")
elif src.count('factor_desc = 1 - (v.descuento_extra_pct or 0) / 100') >= 2:
    res.append("* cancelacion: ya aplicaba el descuento general")
else:
    res.append("ERROR: no se encontro el calculo de importe en cancelar_venta")

# ============================================================
# 3. Bloquear devolucion sobre venta ya devuelta por completo
# ============================================================
viejo3 = '''    if (v.estado or "activa") == "devolucion":
        raise HTTPException(status_code=400, detail="Ese registro ya es una devolución")

    items = data.get("items") or []'''
nuevo3 = '''    if (v.estado or "activa") == "devolucion":
        raise HTTPException(status_code=400, detail="Ese registro ya es una devolución")
    if (v.estado or "activa") == "devuelta":
        raise HTTPException(status_code=400, detail="Esta venta ya fue devuelta por completo")

    items = data.get("items") or []'''
if viejo3 in src:
    src = src.replace(viejo3, nuevo3, 1)
    res.append("OK: se bloquea devolver sobre una venta ya devuelta")
elif src.count('ya fue devuelta por completo') >= 2:
    res.append("* ya se bloqueaba la venta devuelta")
else:
    res.append("ADVERTENCIA: no se encontro el bloque de validacion inicial")

# ============================================================
# 4. Exponer cuanto queda por devolver de cada articulo
# ============================================================
viejo4 = '''    detalle = json.loads(v.detalle_json)
    ahorro_productos = round(sum(it.get("ahorro", 0) or 0 for it in detalle), 2)
    ahorro_descuento_extra = round(v.subtotal - v.total, 2)
    cliente = db.query(Cliente).filter(Cliente.id == v.cliente_id).first() if v.cliente_id else None'''
nuevo4 = '''    detalle = json.loads(v.detalle_json)
    ahorro_productos = round(sum(it.get("ahorro", 0) or 0 for it in detalle), 2)
    ahorro_descuento_extra = round(v.subtotal - v.total, 2)
    cliente = db.query(Cliente).filter(Cliente.id == v.cliente_id).first() if v.cliente_id else None

    # Cuanto se ha devuelto ya de cada articulo de esta venta
    _previas = db.query(Venta).filter(Venta.venta_origen_id == v.id).all()
    _ya_dev = {}
    for _d in _previas:
        for _it in json.loads(_d.detalle_json):
            _pid = _it.get("producto_id")
            _ya_dev[_pid] = _ya_dev.get(_pid, 0) + abs(_it.get("cantidad", 0))
    for _linea in detalle:
        _pid = _linea.get("producto_id")
        _dev = _ya_dev.get(_pid, 0)
        _linea["devuelto"] = round(_dev, 3)
        _linea["disponible_devolucion"] = round(_linea.get("cantidad", 0) - _dev, 3)'''
if viejo4 in src:
    src = src.replace(viejo4, nuevo4, 1)
    res.append("OK: el detalle expone devuelto/disponible por articulo")
elif 'disponible_devolucion' in src:
    res.append("* el detalle ya exponia disponible_devolucion")
else:
    res.append("ADVERTENCIA: no se encontro obtener_venta para agregar los campos")

open(MAIN, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)
print()
print("=" * 58)
if any(r.startswith('ERROR') for r in res):
    print("HUBO ERRORES. Revisa antes de reiniciar.")
else:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo.")
    print()
    print("EJEMPLO del bug corregido:")
    print("  Venta: articulo de $350 con 10% de descuento general -> se cobro $315")
    print("  Antes: devolvia $350  (de mas)")
    print("  Ahora: devuelve $315  (correcto)")
