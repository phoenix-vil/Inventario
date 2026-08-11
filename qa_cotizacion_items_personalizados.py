#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Backend: permite articulos personalizados en la cotizacion (mano
de obra, servicios, etc.) que no existen en el inventario.
 - schemas.py: producto_id pasa a opcional, se agrega "nombre"
 - main.py: si no hay producto_id, usa el nombre dado directamente
   sin buscar en Producto
Uso: cd ~/inventario-qa && python3 qa_cotizacion_items_personalizados.py
"""
import os

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. schemas.py
# ============================================================
ruta = os.path.join(QA, 'schemas.py')
src = open(ruta, encoding='utf-8').read()

viejo = '''class ItemCotizacion(BaseModel):
    producto_id: int
    cantidad: float
    precio_unitario: float'''
nuevo = '''class ItemCotizacion(BaseModel):
    producto_id: Optional[int] = None
    nombre: Optional[str] = None
    cantidad: float
    precio_unitario: float'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK schemas.py: producto_id opcional + campo nombre agregado")
elif 'producto_id: Optional[int] = None' in src:
    res.append("* schemas.py: ya estaba actualizado")
else:
    res.append("ERROR schemas.py: no se encontro ItemCotizacion")

# ============================================================
# 2. main.py: logica de crear_cotizacion
# ============================================================
ruta = os.path.join(QA, 'main.py')
src = open(ruta, encoding='utf-8').read()

viejo2 = '''    subtotal = 0.0
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
        })'''
nuevo2 = '''    subtotal = 0.0
    detalle = []
    for item in data.items:
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        if item.producto_id is not None:
            p = db.query(Producto).filter(Producto.id == item.producto_id).first()
            if not p:
                raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
            nombre_item = p.nombre
            pid = p.id
        else:
            nombre_item = (item.nombre or "").strip()
            if not nombre_item:
                raise HTTPException(status_code=400, detail="Los artículos personalizados necesitan una descripción")
            pid = None
        detalle.append({
            "producto_id": pid,
            "nombre": nombre_item,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "importe": importe,
        })'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK main.py: crear_cotizacion soporta articulos personalizados")
elif 'Los artículos personalizados necesitan una descripción' in src:
    res.append("* main.py: ya estaba actualizado")
else:
    res.append("ERROR main.py: no se encontro el bloque de crear_cotizacion")

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
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    import time
    time.sleep(1.5)
    os.system("sudo systemctl status inventario-qa --no-pager | head -6")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
