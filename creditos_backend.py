#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend de "Credito a clientes": tablas Cliente y PagoCredito, columna
cliente_id en Venta, endpoints de clientes, y "credito" como metodo de
pago valido en registrar_venta.
Uso: cd ~/inventario && python3 creditos_backend.py
"""
import os, re, ast

BASE = os.path.expanduser('~/inventario')

# ================================================================
# 1. database.py: tablas Cliente y PagoCredito + columna cliente_id en Venta
# ================================================================
print("1. Actualizando database.py...")
db_path = os.path.join(BASE, 'database.py')
src = open(db_path, encoding='utf-8').read()

if 'class Cliente' in src:
    print("   * Cliente/PagoCredito ya existian, se omite esa parte")
else:
    clases_nuevas = '''class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    limite_credito = Column(Float, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class PagoCredito(Base):
    __tablename__ = "pagos_credito"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, nullable=False, index=True)
    monto = Column(Float, nullable=False)
    metodo_pago = Column(String, default="efectivo")
    operador = Column(String, nullable=True)
    sucursal = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


'''
    marcador = 'def get_db():'
    if marcador in src:
        src = src.replace(marcador, clases_nuevas + marcador, 1)
        print("   OK Cliente y PagoCredito agregados")
    else:
        print("   ERROR: no se encontro 'def get_db():'")

# Agregar cliente_id a la clase Venta
if 'cliente_id' not in src or 'class Venta' in src and re.search(r'class Venta\(Base\):.*?cliente_id', src, re.DOTALL) is None:
    m = re.search(r'(class Venta\(Base\):.*?)(\n\nclass |\n\ndef )', src, re.DOTALL)
    if m and 'cliente_id' not in m.group(1):
        nuevo_bloque = m.group(1).rstrip('\n') + '\n    cliente_id = Column(Integer, nullable=True)\n'
        src = src[:m.start(1)] + nuevo_bloque + src[m.end(1):]
        print("   OK columna cliente_id agregada a Venta")
    elif m:
        print("   * Venta.cliente_id ya existia")
    else:
        print("   ERROR: no se encontro la clase Venta completa")

open(db_path, 'w', encoding='utf-8').write(src)

try:
    ast.parse(open(db_path, encoding='utf-8').read())
    print("   Sintaxis de database.py: OK")
    db_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    db_ok = False

# ================================================================
# 2. schemas.py: CrearCliente, CrearPagoCredito, RegistrarVenta.cliente_id
# ================================================================
print("2. Actualizando schemas.py...")
sch_path = os.path.join(BASE, 'schemas.py')
src = open(sch_path, encoding='utf-8').read()

viejo_rv = '''class RegistrarVenta(BaseModel):
    items: list[ItemVenta]
    descuento_extra_pct: float = Field(default=0.0, ge=0, le=100)
    autorizado_por: Optional[str] = None
    pago_con: Optional[float] = Field(None, ge=0)
    metodo_pago: str = Field(default="efectivo")
    tpv_referencia: Optional[str] = None
    tpv_autorizacion: Optional[str] = None
    tpv_terminal: Optional[str] = None'''

nuevo_rv = '''class RegistrarVenta(BaseModel):
    items: list[ItemVenta]
    descuento_extra_pct: float = Field(default=0.0, ge=0, le=100)
    autorizado_por: Optional[str] = None
    pago_con: Optional[float] = Field(None, ge=0)
    metodo_pago: str = Field(default="efectivo")
    tpv_referencia: Optional[str] = None
    tpv_autorizacion: Optional[str] = None
    tpv_terminal: Optional[str] = None
    cliente_id: Optional[int] = None'''

n = src.count(viejo_rv)
if n == 1:
    src = src.replace(viejo_rv, nuevo_rv, 1)
    print("   OK cliente_id agregado a RegistrarVenta")
elif 'cliente_id: Optional[int] = None' in src:
    print("   * RegistrarVenta.cliente_id ya existia")
else:
    print("   ERROR: no se encontro el texto exacto de RegistrarVenta")

if 'class CrearCliente' not in src:
    src = src.rstrip('\n') + '''


class CrearCliente(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    nota: Optional[str] = Field(None, max_length=500)
    limite_credito: Optional[float] = Field(None, ge=0)


class CrearPagoCredito(BaseModel):
    monto: float = Field(..., gt=0)
    metodo_pago: str = Field(default="efectivo")
    nota: Optional[str] = Field(None, max_length=500)
'''
    print("   OK esquemas CrearCliente / CrearPagoCredito agregados")
else:
    print("   * Esquemas de cliente ya existian")

open(sch_path, 'w', encoding='utf-8').write(src)

try:
    ast.parse(open(sch_path, encoding='utf-8').read())
    print("   Sintaxis de schemas.py: OK")
    sch_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    sch_ok = False

# ================================================================
# 3. main.py: imports + parche a registrar_venta + endpoints de clientes
# ================================================================
print("3. Actualizando main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()
cambios = []

if 'from database import Cliente' not in src:
    m = re.search(r'from database import \([^)]*\)\n', src)
    if m:
        src = src[:m.end()] + 'from database import Cliente, PagoCredito\n' + src[m.end():]
        cambios.append('imports de database agregados')

if 'from schemas import CrearCliente' not in src:
    m = re.search(r'from schemas import \([^)]*\)\n', src)
    if m:
        src = src[:m.end()] + 'from schemas import CrearCliente, CrearPagoCredito\n' + src[m.end():]
        cambios.append('imports de schemas agregados')

# --- Parche 1: metodo valido + logica de pago_con/cambio ---
viejo_1 = '''    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta") else "efectivo"
    if metodo == "tarjeta":
        # En tarjeta no hay cambio; el pago es por el total exacto
        pago_con = total
        cambio = 0.0
    else:
        pago_con = data.pago_con
        cambio = round(pago_con - total, 2) if (pago_con is not None and pago_con >= total) else None'''

nuevo_1 = '''    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "credito") else "efectivo"

    cliente = None
    if metodo == "credito":
        if not data.cliente_id:
            raise HTTPException(status_code=400, detail="Selecciona un cliente para la venta a crédito")
        cliente = db.query(Cliente).filter(Cliente.id == data.cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if metodo == "tarjeta":
        # En tarjeta no hay cambio; el pago es por el total exacto
        pago_con = total
        cambio = 0.0
    elif metodo == "credito":
        # En credito no se cobra en el momento de la venta
        pago_con = None
        cambio = None
    else:
        pago_con = data.pago_con
        cambio = round(pago_con - total, 2) if (pago_con is not None and pago_con >= total) else None'''

n1 = src.count(viejo_1)
if n1 == 1:
    src = src.replace(viejo_1, nuevo_1, 1)
    cambios.append('logica de metodo_pago actualizada (credito)')
elif 'metodo == "credito"' in src:
    print("   * El parche de metodo_pago ya estaba aplicado")
else:
    print("   ERROR: no se encontro el bloque exacto de metodo/pago_con/cambio")

# --- Parche 2: guardar cliente_id en la Venta ---
viejo_2 = '''        metodo_pago=metodo,
        tpv_referencia=data.tpv_referencia if metodo == "tarjeta" else None,'''
nuevo_2 = '''        metodo_pago=metodo,
        cliente_id=data.cliente_id if metodo == "credito" else None,
        tpv_referencia=data.tpv_referencia if metodo == "tarjeta" else None,'''

n2 = src.count(viejo_2)
if n2 == 1:
    src = src.replace(viejo_2, nuevo_2, 1)
    cambios.append('cliente_id agregado a la creacion de Venta')
elif 'cliente_id=data.cliente_id if metodo == "credito"' in src:
    print("   * cliente_id ya se guardaba en Venta")
else:
    print("   ERROR: no se encontro el bloque exacto de creacion de Venta")

# --- Parche 3: incluir datos del cliente en la respuesta ---
viejo_3 = '''        "metodo_pago": metodo,
        "tpv_referencia": venta.tpv_referencia,'''
nuevo_3 = '''        "metodo_pago": metodo,
        "cliente_id": venta.cliente_id,
        "cliente_nombre": cliente.nombre if cliente else None,
        "tpv_referencia": venta.tpv_referencia,'''

n3 = src.count(viejo_3)
if n3 == 1:
    src = src.replace(viejo_3, nuevo_3, 1)
    cambios.append('cliente incluido en la respuesta de la venta')
elif '"cliente_nombre": cliente.nombre' in src:
    print("   * cliente ya se incluia en la respuesta")
else:
    print("   ERROR: no se encontro el bloque exacto del return")

# --- Endpoints de clientes ---
if '/api/clientes' not in src:
    endpoints = '''

# ─── Clientes y ventas a credito ────────────────────────────────────────────
def _saldo_cliente(db, cliente_id):
    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
    suma_ventas = sum(v.total for v in ventas)
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).all()
    suma_pagos = sum(p.monto for p in pagos)
    return round(suma_ventas - suma_pagos, 2)


@app.post("/api/clientes", status_code=201)
def crear_cliente(data: CrearCliente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = Cliente(
        nombre=data.nombre.strip(),
        telefono=data.telefono,
        nota=data.nota,
        limite_credito=data.limite_credito,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "nombre": c.nombre, "telefono": c.telefono, "limite_credito": c.limite_credito, "saldo": 0.0}


@app.get("/api/clientes")
def listar_clientes(q: Optional[str] = Query(None), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    query = db.query(Cliente)
    if q:
        query = query.filter(Cliente.nombre.ilike(f"%{q}%"))
    clientes = query.order_by(Cliente.nombre).all()
    return [{
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "limite_credito": c.limite_credito,
        "saldo": _saldo_cliente(db, c.id),
    } for c in clientes]


@app.get("/api/clientes/{cliente_id}")
def detalle_cliente(cliente_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").order_by(Venta.creado_en.desc()).all()
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
        } for v in ventas],
        "pagos": [{
            "id": p.id, "monto": p.monto, "metodo_pago": p.metodo_pago,
            "fecha": p.creado_en.isoformat() + "Z", "operador": p.operador, "nota": p.nota,
        } for p in pagos],
    }


@app.patch("/api/clientes/{cliente_id}")
def editar_cliente(cliente_id: int, data: CrearCliente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    c.nombre = data.nombre.strip()
    c.telefono = data.telefono
    c.nota = data.nota
    c.limite_credito = data.limite_credito
    db.commit()
    return {"ok": True}


@app.delete("/api/clientes/{cliente_id}", status_code=204)
def eliminar_cliente(cliente_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    saldo = _saldo_cliente(db, cliente_id)
    if saldo > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: el cliente debe {saldo}")
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if c:
        db.delete(c)
        db.commit()


@app.post("/api/clientes/{cliente_id}/pagos", status_code=201)
def registrar_pago_credito(cliente_id: int, data: CrearPagoCredito, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "transferencia") else "efectivo"
    p = PagoCredito(
        cliente_id=cliente_id,
        monto=data.monto,
        metodo_pago=metodo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        nota=data.nota,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "saldo_restante": _saldo_cliente(db, cliente_id)}


@app.get("/api/clientes-resumen")
def resumen_clientes(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    clientes = db.query(Cliente).all()
    total_por_cobrar = 0.0
    num_con_saldo = 0
    for c in clientes:
        saldo = _saldo_cliente(db, c.id)
        if saldo > 0:
            total_por_cobrar += saldo
            num_con_saldo += 1
    return {"total_por_cobrar": round(total_por_cobrar, 2), "num_clientes_con_saldo": num_con_saldo}


@app.get("/clientes", response_class=FileResponse)
def clientes_page():
    return FileResponse("static/clientes.html")
'''
    src = src.rstrip('\n') + '\n' + endpoints + '\n'
    cambios.append('endpoints de clientes + ruta /clientes agregados')

if cambios:
    open(main_path, 'w', encoding='utf-8').write(src)
    for c in cambios:
        print("   OK " + c)
else:
    print("   * Nada nuevo que aplicar en main.py")

try:
    ast.parse(open(main_path, encoding='utf-8').read())
    print("   Sintaxis de main.py: OK")
    main_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis en main.py, linea " + str(e.lineno) + ": " + str(e.text))
    main_ok = False

print()
print("=" * 55)
if db_ok and sch_ok and main_ok:
    print("Todo compila. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Backend de creditos listo. Ahora corre el script del FRONTEND.")
else:
    print("ADVERTENCIA: hay errores de sintaxis arriba. NO se reinicio el servicio.")
