#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend del modulo de Gastos: tabla + endpoints + integracion con Dashboard
(ganancia neta = ganancia bruta - gastos del periodo).
Uso: cd ~/inventario && python3 gastos_backend.py
"""
import os, re, ast

BASE = os.path.expanduser('~/inventario')

# ================================================================
# 1. database.py: tabla Gasto
# ================================================================
print("1. Agregando tabla Gasto a database.py...")
db_path = os.path.join(BASE, 'database.py')
src = open(db_path, encoding='utf-8').read()

if 'class Gasto' in src:
    print("   * Ya existia, se omite")
else:
    clase_nueva = '''class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    monto = Column(Float, nullable=False)
    metodo_pago = Column(String, default="efectivo")  # efectivo | tarjeta | transferencia
    sucursal = Column(String, nullable=True)
    operador = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    creado_en = Column(DateTime, default=datetime.utcnow)


'''
    marcador = 'def get_db():'
    if marcador in src:
        src = src.replace(marcador, clase_nueva + marcador, 1)
        open(db_path, 'w', encoding='utf-8').write(src)
        print("   OK clase agregada")
    else:
        print("   ERROR: no se encontro 'def get_db():'")

try:
    ast.parse(open(db_path, encoding='utf-8').read())
    print("   Sintaxis de database.py: OK")
    db_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    db_ok = False

# ================================================================
# 2. schemas.py: esquema CrearGasto
# ================================================================
print("2. Agregando esquema CrearGasto a schemas.py...")
sch_path = os.path.join(BASE, 'schemas.py')
src = open(sch_path, encoding='utf-8').read()

if 'class CrearGasto' in src:
    print("   * Ya existia, se omite")
else:
    src = src.rstrip('\n') + '''


class CrearGasto(BaseModel):
    concepto: str = Field(..., min_length=1, max_length=200)
    categoria: str = Field(..., min_length=1, max_length=100)
    monto: float = Field(..., gt=0)
    metodo_pago: str = Field(default="efectivo")
    fecha: Optional[datetime] = None
    nota: Optional[str] = Field(None, max_length=500)
'''
    open(sch_path, 'w', encoding='utf-8').write(src)
    print("   OK esquema agregado")

try:
    ast.parse(open(sch_path, encoding='utf-8').read())
    print("   Sintaxis de schemas.py: OK")
    sch_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    sch_ok = False

# ================================================================
# 3. main.py: imports (lineas separadas) + endpoints + integracion Dashboard
# ================================================================
print("3. Agregando imports y endpoints de Gastos a main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()
cambios = []

if 'from database import Gasto' not in src:
    m = re.search(r'from database import \([^)]*\)\n', src)
    if m:
        src = src[:m.end()] + 'from database import Gasto\n' + src[m.end():]
        cambios.append('import Gasto agregado')

if 'from schemas import CrearGasto' not in src:
    m = re.search(r'from schemas import \([^)]*\)\n', src)
    if m:
        src = src[:m.end()] + 'from schemas import CrearGasto\n' + src[m.end():]
        cambios.append('import CrearGasto agregado')

if '/api/gastos' not in src:
    endpoints = '''

# ─── Gastos del negocio ─────────────────────────────────────────────────────
def _rango_utc_gastos(desde, hasta):
    d = h = None
    if desde:
        try:
            d = datetime.fromisoformat(desde.replace("Z", "+00:00"))
            if d.tzinfo:
                d = d.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            pass
    if hasta:
        try:
            h = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
            if h.tzinfo:
                h = h.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            pass
    return d, h


@app.post("/api/gastos", status_code=201)
def crear_gasto(data: CrearGasto, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "transferencia") else "efectivo"
    g = Gasto(
        concepto=data.concepto.strip(),
        categoria=data.categoria.strip(),
        monto=data.monto,
        metodo_pago=metodo,
        sucursal=sesion.sucursal,
        operador=sesion.usuario,
        nota=data.nota,
        fecha=data.fecha or datetime.utcnow(),
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id}


@app.get("/api/gastos")
def listar_gastos(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(Gasto)
    if d:
        q = q.filter(Gasto.fecha >= d)
    if h:
        q = q.filter(Gasto.fecha <= h)
    if categoria:
        q = q.filter(Gasto.categoria == categoria)
    if sucursal:
        q = q.filter(Gasto.sucursal == sucursal)
    rows = q.order_by(Gasto.fecha.desc()).all()
    return [{
        "id": g.id,
        "concepto": g.concepto,
        "categoria": g.categoria,
        "monto": g.monto,
        "metodo_pago": g.metodo_pago,
        "sucursal": g.sucursal,
        "operador": g.operador,
        "nota": g.nota,
        "fecha": g.fecha.isoformat() + "Z",
    } for g in rows]


@app.get("/api/gastos/categorias")
def categorias_gastos(sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    rows = db.query(Gasto.categoria).distinct().order_by(Gasto.categoria).all()
    return [r[0] for r in rows if r[0]]


@app.get("/api/gastos/resumen")
def resumen_gastos(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(Gasto)
    if d:
        q = q.filter(Gasto.fecha >= d)
    if h:
        q = q.filter(Gasto.fecha <= h)
    gastos = q.all()
    total = round(sum(g.monto for g in gastos), 2)

    por_cat = {}
    for g in gastos:
        por_cat.setdefault(g.categoria, 0.0)
        por_cat[g.categoria] += g.monto
    desglose = sorted(
        [{"categoria": k, "total": round(v, 2)} for k, v in por_cat.items()],
        key=lambda x: x["total"], reverse=True
    )
    return {"total": total, "num_gastos": len(gastos), "por_categoria": desglose}


@app.delete("/api/gastos/{gasto_id}", status_code=204)
def borrar_gasto(gasto_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(g)
    db.commit()


@app.get("/gastos", response_class=FileResponse)
def gastos_page():
    return FileResponse("static/gastos.html")
'''
    src = src.rstrip('\n') + '\n' + endpoints + '\n'
    cambios.append('Endpoints de gastos + ruta /gastos agregados')

# ================================================================
# 4. Integrar Gastos al Dashboard: ganancia neta = ganancia - gastos
# ================================================================
if '"ganancia_neta"' not in src:
    marcador_dash = '    actual["comparativo"] = comparativo\n    return actual'
    if marcador_dash in src:
        bloque_gastos = '''    # Gastos del mismo periodo, para calcular la ganancia neta real
    gastos_q = db.query(Gasto)
    if d:
        gastos_q = gastos_q.filter(Gasto.fecha >= d)
    gastos_total = round(sum(g.monto for g in gastos_q.all()), 2)
    actual["gastos"] = gastos_total
    actual["ganancia_neta"] = round(actual["ganancia"] - gastos_total, 2)

    actual["comparativo"] = comparativo
    return actual'''
        src = src.replace(marcador_dash, bloque_gastos, 1)
        cambios.append('Ganancia neta agregada a /api/dashboard/resumen')
    else:
        print("   ADVERTENCIA: no se encontro el final de dashboard_resumen para integrar gastos")
        print("   (el modulo de Gastos funciona igual, solo no se conecto al Dashboard)")

if cambios:
    open(main_path, 'w', encoding='utf-8').write(src)
    for c in cambios:
        print("   OK " + c)
else:
    print("   * Todo ya existia")

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
    print("Backend de Gastos listo. La tabla se crea sola al iniciar.")
    print("Ahora corre el script del FRONTEND (crea la pagina gastos.html).")
else:
    print("ADVERTENCIA: hay errores de sintaxis arriba. NO se reinicio el servicio.")
