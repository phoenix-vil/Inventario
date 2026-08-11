#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Backend: agrega GET /api/pos/producto/{id}, que devuelve un
producto individual (mismo formato que /api/pos/buscar) para poder
reconstruir el carrito de Punto de Venta a partir de una cotizacion.
Uso: cd ~/inventario-qa && python3 qa_backend_importar_cotizacion.py
"""
import os

MAIN = os.path.expanduser('~/inventario-qa/main.py')
src = open(MAIN, encoding='utf-8').read()

if '/api/pos/producto/' in src:
    print("* El endpoint ya existia")
else:
    marcador = '@app.get("/api/pos/buscar")'
    if marcador not in src:
        print("ERROR: no se encontro el marcador de /api/pos/buscar")
    else:
        endpoint = '''@app.get("/api/pos/producto/{producto_id}")
def pos_producto(producto_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    ahora = datetime.utcnow()
    precio_final = p.precio_venta
    if p.descuento_pct and p.descuento_pct > 0:
        desde_ok = (p.descuento_desde is None) or (p.descuento_desde <= ahora)
        hasta_ok = (p.descuento_hasta is None) or (p.descuento_hasta >= ahora)
        if desde_ok and hasta_ok:
            precio_final = round(p.precio_venta * (1 - p.descuento_pct / 100), 2)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "categoria": p.categoria,
        "precio_venta": p.precio_venta,
        "precio_final": precio_final,
        "stock": p.stock,
        "unidad": p.unidad,
        "vendido_por_peso": bool(p.vendido_por_peso),
        "codigo_barras": p.codigo_barras,
    }


'''
        src = src.replace(marcador, endpoint + marcador, 1)
        open(MAIN, 'w', encoding='utf-8').write(src)
        print("OK: endpoint /api/pos/producto/{id} agregado")

print()
try:
    compile(open(MAIN, encoding='utf-8').read(), MAIN, 'exec')
    print("main.py: sintaxis Python OK")
    sintaxis_ok = True
except SyntaxError as e:
    print("ERROR de sintaxis, linea", e.lineno, ":", e.msg)
    sintaxis_ok = False

print()
print("=" * 58)
if sintaxis_ok:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    import time
    time.sleep(1.5)
    os.system("sudo systemctl status inventario-qa --no-pager | head -6")
else:
    print("Revisa el error. NO se reinicio el servicio.")
