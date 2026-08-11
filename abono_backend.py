#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1. Calcula el saldo pendiente POR VENTA (FIFO: los pagos se aplican
   primero a la venta mas antigua) en detalle_cliente().
2. Enriquece la respuesta de registrar_pago_credito() con todos los
   datos necesarios para generar un recibo.
Uso: cd ~/inventario && python3 abono_backend.py
"""
import os, re, ast

MAIN = os.path.expanduser('~/inventario/main.py')
src = open(MAIN, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Helper de asignacion FIFO (antes de detalle_cliente)
# ================================================================
if '_asignar_pagos_fifo' not in src:
    helper = '''

def _asignar_pagos_fifo(ventas, total_pagos):
    """Aplica los pagos a las ventas mas antiguas primero (FIFO)."""
    ventas_orden_asc = sorted(ventas, key=lambda v: v.creado_en)
    restante = total_pagos
    resultado = {}
    for v in ventas_orden_asc:
        if restante >= v.total:
            pagado = v.total
            restante = round(restante - v.total, 2)
        else:
            pagado = restante
            restante = 0.0
        resultado[v.id] = {"pagado": round(pagado, 2), "saldo": round(v.total - pagado, 2)}
    return resultado
'''
    marcador = '@app.get("/api/clientes/{cliente_id}")'
    if marcador in src:
        src = src.replace(marcador, helper.strip('\n') + '\n\n\n' + marcador, 1)
        cambios.append('helper _asignar_pagos_fifo agregado')
    else:
        print("ERROR: no se encontro el endpoint GET /api/clientes/{cliente_id}")

# ================================================================
# 2. detalle_cliente: usar la asignacion FIFO para cada venta
# ================================================================
viejo_detalle = '''    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").order_by(Venta.creado_en.desc()).all()
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).order_by(PagoCredito.creado_en.desc()).all()
    return {
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "nota": c.nota,
        "limite_credito": c.limite_credito,
        "saldo": _saldo_cliente(db, cliente_id),
        "ventas": [{
            "id": v.id, "total": v.total, "fecha": v.creado_en.isoformat() + "Z",
            "operador": v.operador, "sucursal": v.sucursal,
        } for v in ventas],'''

nuevo_detalle = '''    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").order_by(Venta.creado_en.desc()).all()
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).order_by(PagoCredito.creado_en.desc()).all()
    total_pagos = sum(p.monto for p in pagos)
    asignacion = _asignar_pagos_fifo(ventas, total_pagos)
    return {
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "nota": c.nota,
        "limite_credito": c.limite_credito,
        "saldo": _saldo_cliente(db, cliente_id),
        "ventas": [{
            "id": v.id, "total": v.total, "fecha": v.creado_en.isoformat() + "Z",
            "operador": v.operador, "sucursal": v.sucursal,
            "pagado": asignacion[v.id]["pagado"], "saldo": asignacion[v.id]["saldo"],
        } for v in ventas],'''

n1 = src.count(viejo_detalle)
if n1 == 1:
    src = src.replace(viejo_detalle, nuevo_detalle, 1)
    cambios.append('detalle_cliente ahora incluye pagado/saldo por venta (FIFO)')
elif '"pagado": asignacion[v.id]' in src:
    print("* detalle_cliente ya estaba actualizado")
else:
    print("ERROR: no se encontro el bloque exacto de detalle_cliente")

# ================================================================
# 3. registrar_pago_credito: enriquecer la respuesta para el recibo
# ================================================================
viejo_pago = '''    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "saldo_restante": _saldo_cliente(db, cliente_id)}'''

nuevo_pago = '''    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "id": p.id,
        "saldo_restante": _saldo_cliente(db, cliente_id),
        "cliente_nombre": c.nombre,
        "monto": p.monto,
        "metodo_pago": p.metodo_pago,
        "operador": p.operador,
        "sucursal": p.sucursal,
        "nota": p.nota,
        "fecha": p.creado_en.isoformat() + "Z",
    }'''

n2 = src.count(viejo_pago)
if n2 == 1:
    src = src.replace(viejo_pago, nuevo_pago, 1)
    cambios.append('registrar_pago_credito enriquecido para el recibo')
elif '"cliente_nombre": c.nombre,' in src:
    print("* registrar_pago_credito ya estaba actualizado")
else:
    print("ERROR: no se encontro el bloque exacto de registrar_pago_credito")

if src != original:
    open(MAIN, 'w', encoding='utf-8').write(src)
    print()
    for c in cambios:
        print("OK " + c)

try:
    ast.parse(open(MAIN, encoding='utf-8').read())
    print("\nSintaxis de main.py: OK")
    ok = True
except SyntaxError as e:
    print("\nERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    ok = False

print()
print("=" * 55)
if ok:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Backend listo. Ahora corre el script del FRONTEND.")
else:
    print("ADVERTENCIA: no se reinicio el servicio por el error de arriba.")
