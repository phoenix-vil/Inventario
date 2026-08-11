#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega limites a las ventas en espera:
1. Maximo 2 ventas en espera por sucursal a la vez.
2. Expiran automaticamente a la medianoche (no persisten al dia siguiente).

Uso: cd ~/inventario && python3 limites_ventas_espera.py
"""
import os, re, ast

BASE = os.path.expanduser('~/inventario')

# ================================================================
# 1. schemas.py: agregar hoy_inicio a CrearVentaPendiente
# ================================================================
print("1. Actualizando schemas.py...")
sch_path = os.path.join(BASE, 'schemas.py')
src = open(sch_path, encoding='utf-8').read()

viejo = '''class CrearVentaPendiente(BaseModel):
    carrito: list
    descuento_extra_pct: float = 0.0
    autorizado_por: Optional[str] = None
    nota: Optional[str] = None'''

nuevo = '''class CrearVentaPendiente(BaseModel):
    carrito: list
    descuento_extra_pct: float = 0.0
    autorizado_por: Optional[str] = None
    nota: Optional[str] = None
    hoy_inicio: Optional[str] = None'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    open(sch_path, 'w', encoding='utf-8').write(src)
    print("   OK hoy_inicio agregado a CrearVentaPendiente")
elif 'hoy_inicio' in src:
    print("   * Ya existia")
else:
    print("   ERROR: no se encontro CrearVentaPendiente exacto")

try:
    ast.parse(open(sch_path, encoding='utf-8').read())
    print("   Sintaxis de schemas.py: OK")
    sch_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    sch_ok = False

# ================================================================
# 2. main.py: helper de limpieza + limite de 2 + parametro hoy_inicio
# ================================================================
print("2. Actualizando main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()
cambios = []

# --- Agregar helper de limpieza de vencidas, justo antes del endpoint POST ---
if '_limpiar_pendientes_vencidas' not in src:
    helper = '''

def _limpiar_pendientes_vencidas(db: Session, sucursal, hoy_inicio_str):
    """Elimina ventas en espera creadas antes de la medianoche de hoy (vencidas)."""
    if not hoy_inicio_str:
        return
    try:
        hoy_inicio = datetime.fromisoformat(hoy_inicio_str.replace("Z", "+00:00"))
        if hoy_inicio.tzinfo:
            hoy_inicio = hoy_inicio.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return
    q = db.query(VentaPendiente).filter(VentaPendiente.creado_en < hoy_inicio)
    if sucursal:
        q = q.filter(VentaPendiente.sucursal == sucursal)
    q.delete(synchronize_session=False)
    db.commit()
'''
    marcador = '@app.post("/api/pos/pendientes")'
    if marcador in src:
        src = src.replace(marcador, helper.strip('\n') + '\n\n\n' + marcador, 1)
        cambios.append('helper _limpiar_pendientes_vencidas agregado')
    else:
        print("   ERROR: no se encontro el endpoint POST /api/pos/pendientes")

# --- Modificar crear_pendiente: limpiar vencidas + limite de 2 ---
viejo_crear = '''def crear_pendiente(data: CrearVentaPendiente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    vp = VentaPendiente('''

nuevo_crear = '''def crear_pendiente(data: CrearVentaPendiente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    _limpiar_pendientes_vencidas(db, sesion.sucursal, data.hoy_inicio)

    q_actual = db.query(VentaPendiente)
    if sesion.sucursal:
        q_actual = q_actual.filter(VentaPendiente.sucursal == sesion.sucursal)
    if q_actual.count() >= 2:
        raise HTTPException(
            status_code=400,
            detail="Ya hay 2 ventas en espera en esta sucursal. Cobra o elimina alguna antes de dejar otra en espera."
        )

    vp = VentaPendiente('''

n2 = src.count(viejo_crear)
if n2 == 1:
    src = src.replace(viejo_crear, nuevo_crear, 1)
    cambios.append('limite de 2 + limpieza agregados a crear_pendiente')
elif 'Ya hay 2 ventas en espera' in src:
    print("   * crear_pendiente ya tenia el limite")
else:
    print("   ERROR: no se encontro crear_pendiente exacto")

# --- Modificar listar_pendientes: aceptar hoy_inicio y limpiar vencidas ---
viejo_listar = '''def listar_pendientes(sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    q = db.query(VentaPendiente)'''

nuevo_listar = '''def listar_pendientes(hoy_inicio: Optional[str] = Query(None), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    _limpiar_pendientes_vencidas(db, sesion.sucursal, hoy_inicio)
    q = db.query(VentaPendiente)'''

n3 = src.count(viejo_listar)
if n3 == 1:
    src = src.replace(viejo_listar, nuevo_listar, 1)
    cambios.append('listar_pendientes ahora limpia vencidas')
elif '_limpiar_pendientes_vencidas(db, sesion.sucursal, hoy_inicio)' in src:
    print("   * listar_pendientes ya tenia la limpieza")
else:
    print("   ERROR: no se encontro listar_pendientes exacto")

if cambios:
    open(main_path, 'w', encoding='utf-8').write(src)
    for c in cambios:
        print("   OK " + c)

try:
    ast.parse(open(main_path, encoding='utf-8').read())
    print("   Sintaxis de main.py: OK")
    main_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis en main.py, linea " + str(e.lineno) + ": " + str(e.text))
    main_ok = False

print()
print("=" * 55)
if sch_ok and main_ok:
    print("Todo compila. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Backend listo. Ahora corre el script del FRONTEND.")
else:
    print("ADVERTENCIA: hay errores de sintaxis arriba. NO se reinicio el servicio.")
