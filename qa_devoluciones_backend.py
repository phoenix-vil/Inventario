#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] BACKEND de devoluciones y cancelaciones.
 - database.py: columnas estado / total_devuelto / devoluciones_json en Venta
 - main.py: endpoints POST /api/ventas/{id}/devolucion y /api/ventas/{id}/cancelar
 - main.py: ajusta dashboard, reporte y saldo de clientes para NO contar
   ventas canceladas ni los importes devueltos
Uso: cd ~/inventario-qa && python3 qa_devoluciones_backend.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. database.py — columnas nuevas
# ============================================================
ruta = os.path.join(QA, 'database.py')
src = open(ruta, encoding='utf-8').read()
viejo = '''    cliente_id = Column(Integer, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)'''
nuevo = '''    cliente_id = Column(Integer, nullable=True)
    estado = Column(String, default="activa")  # activa | parcial | cancelada
    total_devuelto = Column(Float, default=0.0)
    devoluciones_json = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK database.py: columnas estado/total_devuelto/devoluciones_json")
elif 'total_devuelto' in src:
    res.append("* database.py: las columnas ya existian")
else:
    res.append("ERROR database.py: no se encontro el bloque del modelo Venta")

# ============================================================
# 2. main.py
# ============================================================
ruta = os.path.join(QA, 'main.py')
src = open(ruta, encoding='utf-8').read()

# --- 2a. Endpoints nuevos ---
if '/api/ventas/{venta_id}/devolucion' in src:
    res.append("* main.py: los endpoints ya existian")
else:
    marcador = '# ─── Buscar producto para POS (por nombre o código) ────────────────────────'
    if marcador not in src:
        res.append("ERROR main.py: no se encontro el marcador para insertar endpoints")
    else:
        endpoints = '''# ─── Devoluciones y cancelaciones ──────────────────────────────────────────
@app.post("/api/ventas/{venta_id}/devolucion")
def devolver_items(
    venta_id: int,
    data: dict = Body(...),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if (v.estado or "activa") == "cancelada":
        raise HTTPException(status_code=400, detail="Esta venta ya fue cancelada")

    items = data.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No se indicaron artículos a devolver")
    motivo = (data.get("motivo") or "").strip() or None

    detalle = json.loads(v.detalle_json)
    devoluciones = json.loads(v.devoluciones_json) if v.devoluciones_json else []

    # Cuanto se ha devuelto ya de cada producto
    ya_devuelto = {}
    for d in devoluciones:
        pid = d.get("producto_id")
        ya_devuelto[pid] = ya_devuelto.get(pid, 0) + d.get("cantidad", 0)

    nuevas = []
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
        nuevas.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": cant,
            "importe": importe,
            "motivo": motivo,
            "operador": sesion.usuario,
            "fecha": datetime.utcnow().isoformat() + "Z",
        })

    if not nuevas:
        raise HTTPException(status_code=400, detail="No se indicaron cantidades válidas")

    # Regresar stock
    for d in nuevas:
        p = db.query(Producto).filter(Producto.id == d["producto_id"]).first()
        if p:
            p.stock = round(p.stock + d["cantidad"], 3)
            p.actualizado_en = datetime.utcnow()

    devoluciones.extend(nuevas)
    v.devoluciones_json = json.dumps(devoluciones, ensure_ascii=False)
    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)

    # Si ya se devolvio todo, marcar como cancelada
    total_items = sum(x.get("cantidad", 0) for x in detalle)
    total_dev = sum(x.get("cantidad", 0) for x in devoluciones)
    v.estado = "cancelada" if total_dev >= total_items - 0.0001 else "parcial"

    db.commit()
    db.refresh(v)
    return {
        "id": v.id,
        "estado": v.estado,
        "monto_devuelto": round(monto_total, 2),
        "total_devuelto": v.total_devuelto,
        "total_original": v.total,
        "total_neto": round(v.total - v.total_devuelto, 2),
        "devoluciones": devoluciones,
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
    if (v.estado or "activa") == "cancelada":
        raise HTTPException(status_code=400, detail="Esta venta ya está cancelada")

    motivo = (data.get("motivo") or "").strip() or None
    detalle = json.loads(v.detalle_json)
    devoluciones = json.loads(v.devoluciones_json) if v.devoluciones_json else []

    ya_devuelto = {}
    for d in devoluciones:
        pid = d.get("producto_id")
        ya_devuelto[pid] = ya_devuelto.get(pid, 0) + d.get("cantidad", 0)

    monto_total = 0.0
    for linea in detalle:
        pid = linea.get("producto_id")
        pendiente = linea.get("cantidad", 0) - ya_devuelto.get(pid, 0)
        if pendiente <= 0:
            continue
        importe = round(linea.get("precio_unitario", 0) * pendiente, 2)
        monto_total += importe
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.stock = round(p.stock + pendiente, 3)
            p.actualizado_en = datetime.utcnow()
        devoluciones.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": pendiente,
            "importe": importe,
            "motivo": motivo or "Cancelación de venta",
            "operador": sesion.usuario,
            "fecha": datetime.utcnow().isoformat() + "Z",
        })

    v.devoluciones_json = json.dumps(devoluciones, ensure_ascii=False)
    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    v.estado = "cancelada"
    db.commit()

    return {
        "id": v.id,
        "estado": "cancelada",
        "monto_devuelto": round(monto_total, 2),
        "total_devuelto": v.total_devuelto,
    }


'''
        src = src.replace(marcador, endpoints + marcador, 1)
        res.append("OK main.py: endpoints de devolucion y cancelacion agregados")

# --- 2b. Asegurar import de Body ---
if re.search(r'from fastapi import[^\n]*\bBody\b', src) is None:
    m = re.search(r'from fastapi import ([^\n]+)', src)
    if m:
        src = src[:m.start()] + 'from fastapi import ' + m.group(1).rstrip() + ', Body' + src[m.end():]
        res.append("OK main.py: import de Body agregado")
    else:
        res.append("ADVERTENCIA main.py: no se encontro el import de fastapi")
else:
    res.append("* main.py: Body ya estaba importado")

# --- 2c. Dashboard: excluir canceladas y restar devoluciones ---
viejo_dash = '''    q = db.query(Venta)
    if desde_dt:
        q = q.filter(Venta.creado_en >= desde_dt)
    if hasta_dt:
        q = q.filter(Venta.creado_en < hasta_dt)
    ventas = q.all()'''
nuevo_dash = '''    q = db.query(Venta).filter((Venta.estado == None) | (Venta.estado != "cancelada"))
    if desde_dt:
        q = q.filter(Venta.creado_en >= desde_dt)
    if hasta_dt:
        q = q.filter(Venta.creado_en < hasta_dt)
    ventas = q.all()'''
if viejo_dash in src:
    src = src.replace(viejo_dash, nuevo_dash, 1)
    res.append("OK main.py: dashboard excluye ventas canceladas")
elif 'Venta.estado != "cancelada"' in src:
    res.append("* main.py: dashboard ya excluia canceladas")
else:
    res.append("ADVERTENCIA main.py: no se encontro el query del dashboard")

viejo_tv = '    total_vendido = round(sum(v.total for v in ventas), 2)'
nuevo_tv = '    total_vendido = round(sum(v.total - (v.total_devuelto or 0) for v in ventas), 2)'
if viejo_tv in src:
    src = src.replace(viejo_tv, nuevo_tv, 1)
    res.append("OK main.py: dashboard resta los importes devueltos")
elif 'v.total_devuelto or 0) for v in ventas' in src:
    res.append("* main.py: dashboard ya restaba devoluciones")

# --- 2d. Reporte completo: mismo ajuste ---
viejo_rep = '''    ventas_q = db.query(Venta)
    if d:
        ventas_q = ventas_q.filter(Venta.creado_en >= d)'''
nuevo_rep = '''    ventas_q = db.query(Venta).filter((Venta.estado == None) | (Venta.estado != "cancelada"))
    if d:
        ventas_q = ventas_q.filter(Venta.creado_en >= d)'''
if viejo_rep in src:
    src = src.replace(viejo_rep, nuevo_rep, 1)
    res.append("OK main.py: reporte excluye ventas canceladas")
elif 'ventas_q = db.query(Venta).filter((Venta.estado' in src:
    res.append("* main.py: reporte ya excluia canceladas")

viejo_rep2 = '    total_vendido = round(sum(v.total for v in ventas), 2)\n\n    por_metodo = {}'
nuevo_rep2 = '    total_vendido = round(sum(v.total - (v.total_devuelto or 0) for v in ventas), 2)\n\n    por_metodo = {}'
if viejo_rep2 in src:
    src = src.replace(viejo_rep2, nuevo_rep2, 1)
    res.append("OK main.py: reporte resta los importes devueltos")

viejo_rep3 = '''        por_metodo[m]["cantidad"] += 1
        por_metodo[m]["total"] += v.total'''
nuevo_rep3 = '''        por_metodo[m]["cantidad"] += 1
        por_metodo[m]["total"] += (v.total - (v.total_devuelto or 0))'''
if viejo_rep3 in src:
    src = src.replace(viejo_rep3, nuevo_rep3, 1)
    res.append("OK main.py: desglose por metodo resta devoluciones")

# --- 2e. Saldo de clientes: no contar ventas canceladas ni devoluciones ---
viejo_saldo = '''    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
    suma_ventas = sum(v.total for v in ventas)'''
nuevo_saldo = '''    ventas = db.query(Venta).filter(
        Venta.cliente_id == cliente_id,
        Venta.metodo_pago == "credito",
        (Venta.estado == None) | (Venta.estado != "cancelada"),
    ).all()
    suma_ventas = sum(v.total - (v.total_devuelto or 0) for v in ventas)'''
if viejo_saldo in src:
    src = src.replace(viejo_saldo, nuevo_saldo, 1)
    res.append("OK main.py: saldo de clientes ignora canceladas y devoluciones")
elif 'suma_ventas = sum(v.total - (v.total_devuelto or 0)' in src:
    res.append("* main.py: saldo de clientes ya estaba ajustado")

# --- 2f. Exponer estado en el listado y el detalle ---
viejo_list = '            "metodo_pago": v.metodo_pago or "efectivo",'
nuevo_list = '            "metodo_pago": v.metodo_pago or "efectivo",\n            "estado": v.estado or "activa",\n            "total_devuelto": v.total_devuelto or 0,'
if viejo_list in src:
    src = src.replace(viejo_list, nuevo_list, 1)
    res.append("OK main.py: listado expone estado y total_devuelto")

viejo_det = '        "metodo_pago": v.metodo_pago or "efectivo",\n        "tpv_referencia": v.tpv_referencia,'
nuevo_det = '        "metodo_pago": v.metodo_pago or "efectivo",\n        "estado": v.estado or "activa",\n        "total_devuelto": v.total_devuelto or 0,\n        "devoluciones": json.loads(v.devoluciones_json) if v.devoluciones_json else [],\n        "tpv_referencia": v.tpv_referencia,'
if viejo_det in src:
    src = src.replace(viejo_det, nuevo_det, 1)
    res.append("OK main.py: detalle expone estado y devoluciones")

open(ruta, 'w', encoding='utf-8').write(src)

# ============================================================
# Resultados
# ============================================================
print()
for r in res:
    print(r)

print()
print("=" * 58)
if any(r.startswith('ERROR') for r in res):
    print("HUBO ERRORES. Revisa arriba antes de continuar.")
else:
    print("PASO SIGUIENTE - migrar la base de datos de QA:")
    print()
    print("  sqlite3 ~/inventario-qa/inventario.db \"ALTER TABLE ventas ADD COLUMN estado TEXT;\"")
    print("  sqlite3 ~/inventario-qa/inventario.db \"ALTER TABLE ventas ADD COLUMN total_devuelto REAL DEFAULT 0;\"")
    print("  sqlite3 ~/inventario-qa/inventario.db \"ALTER TABLE ventas ADD COLUMN devoluciones_json TEXT;\"")
    print()
    print("  sudo systemctl restart inventario-qa")
    print()
    print("Luego confirma que el servicio levanto sin errores:")
    print("  sudo systemctl status inventario-qa --no-pager | head -5")
