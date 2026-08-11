#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] BACKEND de cotizaciones:
 - database.py: modelo Cotizacion
 - schemas.py: ItemCotizacion + RegistrarCotizacion
 - main.py: POST/GET /api/cotizaciones, GET /api/cotizaciones/{id}
   Cualquier operador (requerir_sesion, no requerir_gerente)
Uso: cd ~/inventario-qa && python3 qa_cotizaciones_backend.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. database.py: modelo Cotizacion
# ============================================================
ruta = os.path.join(QA, 'database.py')
src = open(ruta, encoding='utf-8').read()

if 'class Cotizacion(Base)' in src:
    res.append("* database.py: el modelo ya existia")
else:
    modelo = '''

class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    cliente_nombre = Column(String, nullable=True)
    cliente_telefono = Column(String, nullable=True)
    subtotal = Column(Float, nullable=False)
    descuento_extra_pct = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    detalle_json = Column(String, nullable=False)
    operador = Column(String, nullable=True)
    sucursal = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
'''
    marcador = 'class Sucursal(Base):'
    if marcador in src:
        src = src.replace(marcador, modelo.strip() + '\n\n\n' + marcador, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        res.append("OK database.py: modelo Cotizacion agregado")
    else:
        res.append("ERROR database.py: no se encontro el marcador Sucursal")

# ============================================================
# 2. schemas.py
# ============================================================
ruta = os.path.join(QA, 'schemas.py')
src = open(ruta, encoding='utf-8').read()

if 'class RegistrarCotizacion' in src:
    res.append("* schemas.py: ya existia")
else:
    schema = '''

class ItemCotizacion(BaseModel):
    producto_id: int
    cantidad: float
    precio_unitario: float


class RegistrarCotizacion(BaseModel):
    items: list[ItemCotizacion]
    descuento_extra_pct: float = Field(default=0.0, ge=0, le=100)
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None
    nota: Optional[str] = None
'''
    marcador = 'class Login(BaseModel):'
    if marcador in src:
        src = src.replace(marcador, schema.strip() + '\n\n\n' + marcador, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        res.append("OK schemas.py: ItemCotizacion + RegistrarCotizacion agregados")
    else:
        res.append("ERROR schemas.py: no se encontro el marcador Login")

# ============================================================
# 3. main.py: endpoints
# ============================================================
ruta = os.path.join(QA, 'main.py')
src = open(ruta, encoding='utf-8').read()

if '/api/cotizaciones' in src:
    res.append("* main.py: los endpoints ya existian")
else:
    marcador = '# ─── Buscar producto para POS (por nombre o código) ────────────────────────'
    if marcador not in src:
        res.append("ERROR main.py: no se encontro el marcador para insertar")
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
        open(ruta, 'w', encoding='utf-8').write(src)
        res.append("OK main.py: endpoints de cotizaciones agregados (crear/listar/detalle/pagina)")

print()
for r in res:
    print(r)

print()
print("=" * 58)
if any(r.startswith('ERROR') for r in res):
    print("HUBO ERRORES. Revisa antes de continuar.")
else:
    print("PASO SIGUIENTE - crear la tabla en la base de QA:")
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
