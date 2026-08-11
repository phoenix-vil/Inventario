#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Inserta los endpoints de cotizaciones en main.py, justo antes de
la linea de /api/pos/buscar (confirmada por numero de linea).
database.py y schemas.py ya quedaron aplicados en el intento anterior.
Uso: cd ~/inventario-qa && python3 qa_cotizaciones_main_fix.py
"""
import os, re

MAIN = os.path.expanduser('~/inventario-qa/main.py')
src = open(MAIN, encoding='utf-8').read()

if '/api/cotizaciones' in src:
    print("* Los endpoints ya existian, no se hace nada")
else:
    marcador = '@app.get("/api/pos/buscar")'
    if marcador not in src:
        print("ERROR: no se encontro ni siquiera la funcion de referencia")
    else:
        endpoints = '''# ─── Cotizaciones ───────────────────────────────────────────────────────────
@app.post("/api/cotizaciones", status_code=201)
def crear_cotizacion(data: RegistrarCotizacion, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="La cotización no tiene artículos")

    subtotal = 0.0
    detalle = []
    for item in data.items:
        p = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not p:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        detalle.append({
            "producto_id": p.id,
            "nombre": p.nombre,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "importe": importe,
        })

    subtotal = round(subtotal, 2)
    total = round(subtotal * (1 - data.descuento_extra_pct / 100), 2)

    cot = Cotizacion(
        cliente_nombre=(data.cliente_nombre or "").strip() or None,
        cliente_telefono=(data.cliente_telefono or "").strip() or None,
        subtotal=subtotal,
        descuento_extra_pct=data.descuento_extra_pct,
        total=total,
        detalle_json=json.dumps(detalle, ensure_ascii=False),
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        nota=(data.nota or "").strip() or None,
    )
    db.add(cot)
    db.commit()
    db.refresh(cot)

    return {
        "id": cot.id,
        "cliente_nombre": cot.cliente_nombre,
        "cliente_telefono": cot.cliente_telefono,
        "subtotal": subtotal,
        "descuento_extra_pct": data.descuento_extra_pct,
        "total": total,
        "operador": sesion.usuario,
        "sucursal": sesion.sucursal,
        "nota": cot.nota,
        "detalle": detalle,
        "fecha": cot.creado_en.isoformat() + "Z",
    }


@app.get("/api/cotizaciones")
def listar_cotizaciones(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_sesion),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(Cotizacion)
    if d:
        q = q.filter(Cotizacion.creado_en >= d)
    if h:
        q = q.filter(Cotizacion.creado_en <= h)
    cots = q.order_by(Cotizacion.creado_en.desc()).all()
    return [
        {
            "id": c.id,
            "cliente_nombre": c.cliente_nombre,
            "total": c.total,
            "num_items": len(json.loads(c.detalle_json)),
            "operador": c.operador,
            "sucursal": c.sucursal,
            "fecha": c.creado_en.isoformat() + "Z",
        }
        for c in cots
    ]


@app.get("/api/cotizaciones/{cotizacion_id}")
def obtener_cotizacion(cotizacion_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return {
        "id": c.id,
        "cliente_nombre": c.cliente_nombre,
        "cliente_telefono": c.cliente_telefono,
        "subtotal": c.subtotal,
        "descuento_extra_pct": c.descuento_extra_pct,
        "total": c.total,
        "operador": c.operador,
        "sucursal": c.sucursal,
        "nota": c.nota,
        "detalle": json.loads(c.detalle_json),
        "fecha": c.creado_en.isoformat() + "Z",
    }


@app.get("/cotizaciones", response_class=FileResponse)
def cotizaciones_page():
    return FileResponse("static/cotizaciones.html")


'''
        src = src.replace(marcador, endpoints + marcador, 1)
        open(MAIN, 'w', encoding='utf-8').write(src)
        print("OK: endpoints de cotizaciones insertados en main.py")

scripts_ok = True
# Validar que el archivo Python resultante compila
try:
    compile(open(MAIN, encoding='utf-8').read(), MAIN, 'exec')
    print("main.py: sintaxis Python OK")
except SyntaxError as e:
    scripts_ok = False
    print("ERROR de sintaxis en main.py, linea", e.lineno, ":", e.msg)

print()
print("=" * 58)
if scripts_ok:
    print("PASO SIGUIENTE - crear la tabla en la base de QA (si no lo has hecho):")
    print()
    print('  sqlite3 ~/inventario-qa/inventario.db "CREATE TABLE cotizaciones (')
    print('    id INTEGER PRIMARY KEY,')
    print('    cliente_nombre TEXT,')
    print('    cliente_telefono TEXT,')
    print('    subtotal REAL NOT NULL,')
    print('    descuento_extra_pct REAL DEFAULT 0,')
    print('    total REAL NOT NULL,')
    print('    detalle_json TEXT NOT NULL,')
    print('    operador TEXT,')
    print('    sucursal TEXT,')
    print('    nota TEXT,')
    print('    creado_en DATETIME')
    print('  );"')
    print()
    print("  sudo systemctl restart inventario-qa")
    print("  sudo systemctl status inventario-qa --no-pager | head -6")
else:
    print("NO se reinicia el servicio, hay un error de sintaxis que corregir.")
