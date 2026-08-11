#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega un endpoint que devuelve los abonos de credito cobrados en un
periodo (mismos filtros de fecha/sucursal que /api/ventas), para poder
conciliar cuanto dinero real entro al negocio.
Uso: cd ~/inventario && python3 abonos_historial_backend.py
"""
import os, re, ast

MAIN = os.path.expanduser('~/inventario/main.py')
src = open(MAIN, encoding='utf-8').read()
original = src

if '/api/clientes/abonos-periodo' in src:
    print("* El endpoint ya existia, se omite")
else:
    endpoint = '''

@app.get("/api/clientes/abonos-periodo")
def abonos_periodo(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(PagoCredito)
    if d:
        q = q.filter(PagoCredito.creado_en >= d)
    if h:
        q = q.filter(PagoCredito.creado_en <= h)
    if sucursal:
        q = q.filter(PagoCredito.sucursal == sucursal)
    pagos = q.order_by(PagoCredito.creado_en.desc()).all()
    total = round(sum(p.monto for p in pagos), 2)

    cliente_ids = list(set(p.cliente_id for p in pagos))
    clientes_map = {}
    if cliente_ids:
        rows = db.query(Cliente.id, Cliente.nombre).filter(Cliente.id.in_(cliente_ids)).all()
        clientes_map = {r[0]: r[1] for r in rows}

    return {
        "total": total,
        "num_abonos": len(pagos),
        "abonos": [{
            "id": p.id,
            "cliente_nombre": clientes_map.get(p.cliente_id, "Cliente"),
            "monto": p.monto,
            "metodo_pago": p.metodo_pago,
            "operador": p.operador,
            "sucursal": p.sucursal,
            "fecha": p.creado_en.isoformat() + "Z",
            "nota": p.nota,
        } for p in pagos],
    }
'''
    src = src.rstrip('\n') + endpoint + '\n'
    open(MAIN, 'w', encoding='utf-8').write(src)
    print("OK endpoint /api/clientes/abonos-periodo agregado")

try:
    ast.parse(open(MAIN, encoding='utf-8').read())
    print("Sintaxis de main.py: OK")
    ok = True
except SyntaxError as e:
    print("ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    ok = False

print()
print("=" * 55)
if ok:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Backend listo. Ahora corre el script del FRONTEND.")
else:
    print("ADVERTENCIA: no se reinicio el servicio por el error de arriba.")
