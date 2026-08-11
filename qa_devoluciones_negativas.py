#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] REDISENO de devoluciones: en vez de marcar y excluir la venta
original, se crea un REGISTRO NUEVO con total negativo ligado a ella.

 - La venta original queda intacta y visible
 - La devolucion aparece en el historial como su propio movimiento
 - Los totales se corrigen solos al sumar (se revierten los filtros
   de exclusion de ayer, que ahora duplicarian el descuento)

Uso: cd ~/inventario-qa && python3 qa_devoluciones_negativas.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. database.py — columna venta_origen_id
# ============================================================
ruta = os.path.join(QA, 'database.py')
src = open(ruta, encoding='utf-8').read()
viejo = '    estado = Column(String, default="activa")  # activa | parcial | cancelada'
nuevo = ('    estado = Column(String, default="activa")  # activa | parcial | cancelada | devolucion\n'
         '    venta_origen_id = Column(Integer, nullable=True)  # si es devolucion, la venta que la origino')
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK database.py: columna venta_origen_id agregada")
elif 'venta_origen_id' in src:
    res.append("* database.py: venta_origen_id ya existia")
else:
    res.append("ERROR database.py: no se encontro la columna estado")

# ============================================================
# 2. main.py
# ============================================================
ruta = os.path.join(QA, 'main.py')
src = open(ruta, encoding='utf-8').read()

# --- 2a. REVERTIR los filtros de exclusion (ahora duplicarian) ---
rev = [
    ('    q = db.query(Venta).filter((Venta.estado == None) | (Venta.estado != "cancelada"))',
     '    q = db.query(Venta)',
     'dashboard vuelve a incluir todas las ventas'),
    ('    total_vendido = round(sum(v.total - (v.total_devuelto or 0) for v in ventas), 2)\n    total_costo = 0.0',
     '    total_vendido = round(sum(v.total for v in ventas), 2)\n    total_costo = 0.0',
     'dashboard ya no resta total_devuelto'),
    ('    ventas_q = db.query(Venta).filter((Venta.estado == None) | (Venta.estado != "cancelada"))',
     '    ventas_q = db.query(Venta)',
     'reporte vuelve a incluir todas las ventas'),
    ('    total_vendido = round(sum(v.total - (v.total_devuelto or 0) for v in ventas), 2)\n\n    por_metodo = {}',
     '    total_vendido = round(sum(v.total for v in ventas), 2)\n\n    por_metodo = {}',
     'reporte ya no resta total_devuelto'),
    ('        por_metodo[m]["total"] += (v.total - (v.total_devuelto or 0))',
     '        por_metodo[m]["total"] += v.total',
     'desglose por metodo ya no resta total_devuelto'),
    ('''    ventas = db.query(Venta).filter(
        Venta.cliente_id == cliente_id,
        Venta.metodo_pago == "credito",
        (Venta.estado == None) | (Venta.estado != "cancelada"),
    ).all()
    suma_ventas = sum(v.total - (v.total_devuelto or 0) for v in ventas)''',
     '''    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
    suma_ventas = sum(v.total for v in ventas)''',
     'saldo de clientes vuelve al calculo simple'),
]
for viejo_r, nuevo_r, desc in rev:
    if viejo_r in src:
        src = src.replace(viejo_r, nuevo_r, 1)
        res.append("OK revertido: " + desc)
    elif nuevo_r in src:
        res.append("* ya revertido: " + desc)
    else:
        res.append("ADVERTENCIA no se encontro para revertir: " + desc)

# --- 2b. Reemplazar los dos endpoints ---
def cortar_funcion(texto, marca_decorador):
    ini = texto.find(marca_decorador)
    if ini == -1:
        return None, None
    sig = texto.find('\n@app.', ini + 10)
    if sig == -1:
        return None, None
    return ini, sig + 1

NUEVOS = '''@app.post("/api/ventas/{venta_id}/devolucion")
def devolver_items(
    venta_id: int,
    data: dict = Body(...),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if (v.estado or "activa") == "devolucion":
        raise HTTPException(status_code=400, detail="Ese registro ya es una devolución")

    items = data.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No se indicaron artículos a devolver")
    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Indica el motivo de la devolución")

    detalle = json.loads(v.detalle_json)

    # Cuanto se ha devuelto ya de esta venta (sumando devoluciones previas)
    previas = db.query(Venta).filter(Venta.venta_origen_id == venta_id).all()
    ya_devuelto = {}
    for d in previas:
        for it in json.loads(d.detalle_json):
            pid = it.get("producto_id")
            ya_devuelto[pid] = ya_devuelto.get(pid, 0) + abs(it.get("cantidad", 0))

    detalle_dev = []
    monto_total = 0.0
    for it in items:
        pid = it.get("producto_id")
        cant = float(it.get("cantidad") or 0)
        if cant <= 0:
            continue
        linea = next((x for x in detalle if x.get("producto_id") == pid), None)
        if not linea:
            raise HTTPException(status_code=400, detail=f"El producto {pid} no está en esta venta")
        disponible = linea.get("cantidad", 0) - ya_devuelto.get(pid, 0)
        if cant > disponible + 0.0001:
            raise HTTPException(
                status_code=400,
                detail=f"No puedes devolver {cant} de '{linea.get('nombre')}': solo quedan {round(disponible, 3)} por devolver",
            )
        importe = round(linea.get("precio_unitario", 0) * cant, 2)
        monto_total += importe
        detalle_dev.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": -cant,
            "precio_unitario": linea.get("precio_unitario", 0),
            "precio_original": linea.get("precio_original"),
            "ahorro": 0.0,
            "importe": -importe,
        })
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.stock = round(p.stock + cant, 3)
            p.actualizado_en = datetime.utcnow()

    if not detalle_dev:
        raise HTTPException(status_code=400, detail="No se indicaron cantidades válidas")

    monto_total = round(monto_total, 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-monto_total,
        descuento_extra_pct=0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    total_items = sum(x.get("cantidad", 0) for x in detalle)
    total_dev_acum = sum(ya_devuelto.values()) + sum(abs(x["cantidad"]) for x in detalle_dev)
    v.estado = "devuelta" if total_dev_acum >= total_items - 0.0001 else "parcial"

    db.commit()
    db.refresh(dev)
    return {
        "id_devolucion": dev.id,
        "venta_origen": venta_id,
        "monto_devuelto": monto_total,
        "estado_venta_origen": v.estado,
        "total_devuelto_acumulado": v.total_devuelto,
    }


@app.post("/api/ventas/{venta_id}/cancelar")
def cancelar_venta(
    venta_id: int,
    data: dict = Body(default={}),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if (v.estado or "activa") == "devolucion":
        raise HTTPException(status_code=400, detail="Ese registro ya es una devolución")
    if (v.estado or "activa") == "devuelta":
        raise HTTPException(status_code=400, detail="Esta venta ya fue devuelta por completo")

    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Indica el motivo de la cancelación")

    detalle = json.loads(v.detalle_json)
    previas = db.query(Venta).filter(Venta.venta_origen_id == venta_id).all()
    ya_devuelto = {}
    for d in previas:
        for it in json.loads(d.detalle_json):
            pid = it.get("producto_id")
            ya_devuelto[pid] = ya_devuelto.get(pid, 0) + abs(it.get("cantidad", 0))

    detalle_dev = []
    monto_total = 0.0
    for linea in detalle:
        pid = linea.get("producto_id")
        pendiente = linea.get("cantidad", 0) - ya_devuelto.get(pid, 0)
        if pendiente <= 0.0001:
            continue
        importe = round(linea.get("precio_unitario", 0) * pendiente, 2)
        monto_total += importe
        detalle_dev.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": -pendiente,
            "precio_unitario": linea.get("precio_unitario", 0),
            "precio_original": linea.get("precio_original"),
            "ahorro": 0.0,
            "importe": -importe,
        })
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.stock = round(p.stock + pendiente, 3)
            p.actualizado_en = datetime.utcnow()

    if not detalle_dev:
        raise HTTPException(status_code=400, detail="Esta venta ya no tiene artículos por devolver")

    monto_total = round(monto_total, 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-monto_total,
        descuento_extra_pct=0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    v.estado = "devuelta"
    db.commit()
    db.refresh(dev)
    return {
        "id_devolucion": dev.id,
        "venta_origen": venta_id,
        "monto_devuelto": monto_total,
        "estado_venta_origen": "devuelta",
    }


'''

ini, fin = cortar_funcion(src, '@app.post("/api/ventas/{venta_id}/devolucion")')
if ini is None:
    res.append("ERROR main.py: no se encontro el endpoint de devolucion")
else:
    ini2, fin2 = cortar_funcion(src[fin:], '@app.post("/api/ventas/{venta_id}/cancelar")')
    if ini2 is None:
        res.append("ERROR main.py: no se encontro el endpoint de cancelar")
    else:
        src = src[:ini] + NUEVOS + src[fin + fin2:]
        res.append("OK main.py: ambos endpoints reemplazados (registros negativos)")

# --- 2c. Exponer venta_origen_id ---
if '"venta_origen_id": v.venta_origen_id' not in src:
    src = src.replace(
        '            "estado": v.estado or "activa",\n            "total_devuelto": v.total_devuelto or 0,',
        '            "estado": v.estado or "activa",\n            "total_devuelto": v.total_devuelto or 0,\n            "venta_origen_id": v.venta_origen_id,',
        1)
    src = src.replace(
        '        "estado": v.estado or "activa",\n        "total_devuelto": v.total_devuelto or 0,',
        '        "estado": v.estado or "activa",\n        "total_devuelto": v.total_devuelto or 0,\n        "venta_origen_id": v.venta_origen_id,',
        1)
    res.append("OK main.py: venta_origen_id expuesto en listado y detalle")

open(ruta, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)
print()
print("=" * 58)
if any(r.startswith('ERROR') for r in res):
    print("HUBO ERRORES. Revisa antes de continuar.")
else:
    print("PASO SIGUIENTE - migrar QA y reiniciar:")
    print()
    print('  sqlite3 ~/inventario-qa/inventario.db "ALTER TABLE ventas ADD COLUMN venta_origen_id INTEGER;"')
    print("  sudo systemctl restart inventario-qa")
    print("  sudo systemctl status inventario-qa --no-pager | head -6")
