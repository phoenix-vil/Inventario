#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend de "ventas en espera": nueva tabla + 4 endpoints.
Uso: cd ~/inventario && python3 ventas_pendientes_backend.py
"""
import os, re, ast

BASE = os.path.expanduser('~/inventario')

# ================================================================
# 1. database.py: agregar tabla VentaPendiente
# ================================================================
print("1. Agregando tabla VentaPendiente a database.py...")
db_path = os.path.join(BASE, 'database.py')
src = open(db_path, encoding='utf-8').read()

if 'class VentaPendiente' in src:
    print("   * Ya existia, se omite")
else:
    clase_nueva = '''class VentaPendiente(Base):
    __tablename__ = "ventas_pendientes"

    id = Column(Integer, primary_key=True, index=True)
    sucursal = Column(String, nullable=True)
    operador = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    carrito_json = Column(String, nullable=False)
    descuento_extra_pct = Column(Float, default=0.0)
    autorizado_por = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


'''
    marcador = 'def get_db():'
    if marcador in src:
        src = src.replace(marcador, clase_nueva + marcador, 1)
        open(db_path, 'w', encoding='utf-8').write(src)
        print("   OK clase agregada antes de get_db()")
    else:
        print("   ERROR: no se encontro 'def get_db():' en database.py")
        print("   Agrega la clase manualmente.")

# Verificar sintaxis
try:
    ast.parse(open(db_path, encoding='utf-8').read())
    print("   Sintaxis de database.py: OK")
    db_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis en database.py, linea " + str(e.lineno) + ": " + str(e.text))
    db_ok = False

# ================================================================
# 2. schemas.py: agregar esquema CrearVentaPendiente
# ================================================================
print("2. Agregando esquema a schemas.py...")
sch_path = os.path.join(BASE, 'schemas.py')
src = open(sch_path, encoding='utf-8').read()

if 'class CrearVentaPendiente' in src:
    print("   * Ya existia, se omite")
else:
    src = src.rstrip('\n') + '''


class CrearVentaPendiente(BaseModel):
    carrito: list
    descuento_extra_pct: float = 0.0
    autorizado_por: Optional[str] = None
    nota: Optional[str] = None
'''
    open(sch_path, 'w', encoding='utf-8').write(src)
    print("   OK esquema agregado")

try:
    ast.parse(open(sch_path, encoding='utf-8').read())
    print("   Sintaxis de schemas.py: OK")
    sch_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis en schemas.py, linea " + str(e.lineno) + ": " + str(e.text))
    sch_ok = False

# ================================================================
# 3. main.py: imports nuevos (lineas separadas, NUNCA editar el
#    import existente para evitar el bug de comas que ya tuvimos)
#    + los 4 endpoints
# ================================================================
print("3. Agregando imports y endpoints a main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()

cambios = []

if 'from database import VentaPendiente' not in src:
    # Insertar la nueva linea de import justo despues de la primera linea "from database import"
    m = re.search(r'from database import \([^)]*\)\n', src)
    if m:
        src = src[:m.end()] + 'from database import VentaPendiente\n' + src[m.end():]
        cambios.append('import VentaPendiente agregado')
    else:
        print("   ADVERTENCIA: no se encontro el bloque de import de database")

if 'from schemas import CrearVentaPendiente' not in src:
    m = re.search(r'from schemas import \([^)]*\)\n', src)
    if m:
        src = src[:m.end()] + 'from schemas import CrearVentaPendiente\n' + src[m.end():]
        cambios.append('import CrearVentaPendiente agregado')
    else:
        print("   ADVERTENCIA: no se encontro el bloque de import de schemas")

if '/api/pos/pendientes' not in src:
    endpoints = '''

# ─── Ventas en espera ───────────────────────────────────────────────────────
@app.post("/api/pos/pendientes")
def crear_pendiente(data: CrearVentaPendiente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    vp = VentaPendiente(
        sucursal=sesion.sucursal,
        operador=sesion.usuario,
        nota=data.nota,
        carrito_json=json.dumps(data.carrito, ensure_ascii=False),
        descuento_extra_pct=data.descuento_extra_pct,
        autorizado_por=data.autorizado_por,
    )
    db.add(vp)
    db.commit()
    db.refresh(vp)
    return {"id": vp.id}


@app.get("/api/pos/pendientes")
def listar_pendientes(sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    q = db.query(VentaPendiente)
    if sesion.sucursal:
        q = q.filter(VentaPendiente.sucursal == sesion.sucursal)
    rows = q.order_by(VentaPendiente.creado_en.desc()).all()
    resultado = []
    for v in rows:
        carrito = json.loads(v.carrito_json)
        total = sum((it.get('precio', 0) or 0) * (it.get('cantidad', 0) or 0) for it in carrito)
        resultado.append({
            "id": v.id,
            "operador": v.operador,
            "nota": v.nota,
            "num_items": len(carrito),
            "total_aprox": round(total, 2),
            "creado_en": v.creado_en.isoformat() + "Z",
        })
    return resultado


@app.get("/api/pos/pendientes/{pid}")
def obtener_pendiente(pid: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    v = db.query(VentaPendiente).filter(VentaPendiente.id == pid).first()
    if not v:
        raise HTTPException(status_code=404, detail="No encontrada")
    return {
        "id": v.id,
        "carrito": json.loads(v.carrito_json),
        "descuento_extra_pct": v.descuento_extra_pct,
        "autorizado_por": v.autorizado_por,
        "nota": v.nota,
    }


@app.delete("/api/pos/pendientes/{pid}", status_code=204)
def borrar_pendiente(pid: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    v = db.query(VentaPendiente).filter(VentaPendiente.id == pid).first()
    if v:
        db.delete(v)
        db.commit()
'''
    src = src.rstrip('\n') + '\n' + endpoints + '\n'
    cambios.append('4 endpoints de pendientes agregados')

if cambios:
    open(main_path, 'w', encoding='utf-8').write(src)
    for c in cambios:
        print("   OK " + c)
else:
    print("   * Todo ya existia, no se cambio nada")

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
    print("Todo compila correctamente. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Backend listo. La tabla 'ventas_pendientes' se crea sola al iniciar.")
    print("Ahora corre el script del FRONTEND para agregar los botones.")
else:
    print("ADVERTENCIA: hay errores de sintaxis arriba. NO se reinicio el servicio.")
    print("Corrige antes de continuar con el script del frontend.")
