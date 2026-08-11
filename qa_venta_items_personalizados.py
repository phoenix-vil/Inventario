#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Permite articulos personalizados (mano de obra, servicios) en las
VENTAS reales, no solo en cotizaciones:
 - schemas.py: ItemVenta.producto_id opcional + campo nombre
 - main.py registrar_venta: si no hay producto_id, usa el nombre dado,
   sin buscar en Producto ni descontar stock
 - main.py _calcular_periodo_dash: filtra producto_id=None antes de
   consultar costos (evita que un articulo personalizado rompa el
   calculo de ganancia del Dashboard)
Uso: cd ~/inventario-qa && python3 qa_venta_items_personalizados.py
"""
import os

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. schemas.py
# ============================================================
ruta = os.path.join(QA, 'schemas.py')
src = open(ruta, encoding='utf-8').read()

viejo = '''class ItemVenta(BaseModel):
    producto_id: int
    cantidad: float
    precio_unitario: float
    precio_original: Optional[float] = None'''
nuevo = '''class ItemVenta(BaseModel):
    producto_id: Optional[int] = None
    nombre: Optional[str] = None
    cantidad: float
    precio_unitario: float
    precio_original: Optional[float] = None'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta, 'w', encoding='utf-8').write(src)
    res.append("OK schemas.py: ItemVenta.producto_id opcional + campo nombre")
elif 'producto_id: Optional[int] = None' in src and 'class ItemVenta' in src:
    res.append("* schemas.py: ya estaba actualizado")
else:
    res.append("ERROR schemas.py: no se encontro ItemVenta")

# ============================================================
# 2. main.py: registrar_venta
# ============================================================
ruta = os.path.join(QA, 'main.py')
src = open(ruta, encoding='utf-8').read()

viejo2 = '''    subtotal = 0.0
    ahorro_productos = 0.0
    detalle = []
    productos_map = {}
    for item in data.items:
        p = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not p:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
        # Restriccion de stock desactivada: se permite vender con stock 0 o negativo
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        productos_map[p.id] = p
        ahorro_item = 0.0
        if item.precio_original is not None and item.precio_original > item.precio_unitario:
            ahorro_item = round((item.precio_original - item.precio_unitario) * item.cantidad, 2)
            ahorro_productos += ahorro_item
        detalle.append({
            "producto_id": p.id,
            "nombre": p.nombre,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "precio_original": item.precio_original,
            "ahorro": ahorro_item,
            "importe": importe,
        })'''
nuevo2 = '''    subtotal = 0.0
    ahorro_productos = 0.0
    detalle = []
    productos_map = {}
    for item in data.items:
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        ahorro_item = 0.0
        if item.precio_original is not None and item.precio_original > item.precio_unitario:
            ahorro_item = round((item.precio_original - item.precio_unitario) * item.cantidad, 2)
            ahorro_productos += ahorro_item

        if item.producto_id is not None:
            # Restriccion de stock desactivada: se permite vender con stock 0 o negativo
            p = db.query(Producto).filter(Producto.id == item.producto_id).first()
            if not p:
                raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
            productos_map[p.id] = p
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
            "precio_original": item.precio_original,
            "ahorro": ahorro_item,
            "importe": importe,
        })'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    res.append("OK main.py: registrar_venta soporta articulos personalizados")
elif 'Los artículos personalizados necesitan una descripción' in src:
    res.append("* main.py: registrar_venta ya estaba actualizado")
else:
    res.append("ERROR main.py: no se encontro el bloque principal de registrar_venta")

viejo3 = '''    # Descontar stock
    for item in data.items:
        p = productos_map[item.producto_id]
        p.stock = round(p.stock - item.cantidad, 3)
        p.actualizado_en = datetime.utcnow()'''
nuevo3 = '''    # Descontar stock (solo articulos con producto real; los
    # personalizados -mano de obra, servicios- no tienen inventario)
    for item in data.items:
        if item.producto_id is None:
            continue
        p = productos_map[item.producto_id]
        p.stock = round(p.stock - item.cantidad, 3)
        p.actualizado_en = datetime.utcnow()'''
if viejo3 in src:
    src = src.replace(viejo3, nuevo3, 1)
    res.append("OK main.py: descuento de stock omite articulos personalizados")
elif 'no tienen inventario' in src:
    res.append("* main.py: descuento de stock ya estaba actualizado")
else:
    res.append("ERROR main.py: no se encontro el bloque de descuento de stock")

# ============================================================
# 3. main.py: _calcular_periodo_dash (defensivo, evita romper Dashboard)
# ============================================================
viejo4 = '''    ids = set()
    detalles = []
    for v in ventas:
        det = json.loads(v.detalle_json)
        detalles.append(det)
        for it in det:
            ids.add(it.get("producto_id"))
    costos = _costo_por_producto_dash(db, ids)'''
nuevo4 = '''    ids = set()
    detalles = []
    for v in ventas:
        det = json.loads(v.detalle_json)
        detalles.append(det)
        for it in det:
            pid = it.get("producto_id")
            if pid is not None:
                ids.add(pid)
    costos = _costo_por_producto_dash(db, ids)'''
if viejo4 in src:
    src = src.replace(viejo4, nuevo4, 1)
    res.append("OK main.py: Dashboard filtra producto_id=None antes de calcular costos")
elif 'if pid is not None:\n                ids.add(pid)' in src:
    res.append("* main.py: Dashboard ya estaba actualizado")
else:
    res.append("ADVERTENCIA main.py: no se encontro el bloque de _calcular_periodo_dash (revisar Dashboard manualmente)")

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
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    import time
    time.sleep(1.5)
    os.system("sudo systemctl status inventario-qa --no-pager | head -6")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
