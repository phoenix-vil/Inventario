#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Backend: agrega venta_id a Cotizacion (referencia a la venta que
la cobro) y el endpoint para marcarla. Tambien la expone en los listados.
Uso: cd ~/inventario-qa && python3 qa_cotizacion_marcar_vendida.py
"""
import os

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. database.py: columna venta_id
# ============================================================
ruta = os.path.join(QA, 'database.py')
src = open(ruta, encoding='utf-8').read()
viejo = '''    nota = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sucursal(Base):'''
nuevo = '''    nota = Column(String, nullable=True)
    venta_id = Column(Integer, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sucursal(Base):'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK database.py: columna venta_id agregada a Cotizacion")
elif 'venta_id = Column(Integer, nullable=True)' in src and src.count('venta_id') >= 1:
    res.append("* database.py: ya existia (revisar si es en el modelo correcto)")
else:
    res.append("ERROR database.py: no se encontro el bloque exacto de Cotizacion")

# ============================================================
# 2. main.py: endpoint para marcar vendida + exponer venta_id
# ============================================================
ruta = os.path.join(QA, 'main.py')
src = open(ruta, encoding='utf-8').read()

if '/marcar-vendida' in src:
    res.append("* main.py: el endpoint ya existia")
else:
    marcador = '@app.get("/api/cotizaciones")'
    if marcador not in src:
        res.append("ERROR main.py: no se encontro el marcador GET /api/cotizaciones")
    else:
        endpoint = '''@app.post("/api/cotizaciones/{cotizacion_id}/marcar-vendida")
def marcar_cotizacion_vendida(cotizacion_id: int, data: dict = Body(...), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    venta_id = data.get("venta_id")
    if not venta_id:
        raise HTTPException(status_code=400, detail="Falta venta_id")
    c.venta_id = venta_id
    db.commit()
    return {"id": c.id, "venta_id": c.venta_id}


'''
        src = src.replace(marcador, endpoint + marcador, 1)
        res.append("OK main.py: endpoint POST /marcar-vendida agregado")

# Exponer venta_id en el listado
viejo_list = '''            "operador": c.operador,
            "sucursal": c.sucursal,
            "fecha": c.creado_en.isoformat() + "Z",
        }
        for c in cots
    ]'''
nuevo_list = '''            "operador": c.operador,
            "sucursal": c.sucursal,
            "venta_id": c.venta_id,
            "fecha": c.creado_en.isoformat() + "Z",
        }
        for c in cots
    ]'''
if viejo_list in src:
    src = src.replace(viejo_list, nuevo_list, 1)
    res.append("OK main.py: listado de cotizaciones expone venta_id")
elif '"venta_id": c.venta_id,\n            "fecha"' in src:
    res.append("* main.py: el listado ya exponia venta_id")
else:
    res.append("ERROR main.py: no se encontro el bloque de retorno del listado")

# Exponer venta_id en el detalle
viejo_det = '''        "operador": c.operador,
        "sucursal": c.sucursal,
        "nota": c.nota,
        "detalle": json.loads(c.detalle_json),
        "fecha": c.creado_en.isoformat() + "Z",
    }'''
nuevo_det = '''        "operador": c.operador,
        "sucursal": c.sucursal,
        "nota": c.nota,
        "venta_id": c.venta_id,
        "detalle": json.loads(c.detalle_json),
        "fecha": c.creado_en.isoformat() + "Z",
    }'''
if viejo_det in src:
    src = src.replace(viejo_det, nuevo_det, 1)
    res.append("OK main.py: detalle de cotizacion expone venta_id")
elif '"venta_id": c.venta_id,\n        "detalle"' in src:
    res.append("* main.py: el detalle ya exponia venta_id")
else:
    res.append("ERROR main.py: no se encontro el bloque de retorno del detalle")

open(ruta, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

print()
try:
    compile(open(ruta, encoding='utf-8').read(), ruta, 'exec')
    print("main.py: sintaxis Python OK")
    sintaxis_ok = True
except SyntaxError as e:
    print("ERROR de sintaxis, linea", e.lineno, ":", e.msg)
    sintaxis_ok = False

print()
print("=" * 58)
if sintaxis_ok and not any(r.startswith('ERROR') for r in res):
    print("PASO SIGUIENTE - migrar la base de QA:")
    print('  sqlite3 ~/inventario-qa/inventario.db "ALTER TABLE cotizaciones ADD COLUMN venta_id INTEGER;"')
    print()
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    import time
    time.sleep(1.5)
    os.system("sudo systemctl status inventario-qa --no-pager | head -6")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
