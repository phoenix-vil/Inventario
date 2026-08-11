#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige los 3 puntos pendientes de devoluciones:
 1. BACKEND: obtener_venta expone devuelto/disponible por articulo
    (la pantalla los leia de devoluciones_json, vacio tras el rediseno)
 2. PANTALLA: el estado ahora es 'devuelta', no 'cancelada' -> por eso
    los botones no se bloqueaban al devolver todo
 3. PANTALLA: botones del modal lado a lado (no apilados al 100%)
Uso: cd ~/inventario-qa && python3 qa_fix_devoluciones_pantalla.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. BACKEND: devuelto/disponible por articulo en obtener_venta
# ============================================================
MAIN = os.path.join(QA, 'main.py')
src = open(MAIN, encoding='utf-8').read()

viejo = '''    detalle = json.loads(v.detalle_json)
    ahorro_productos = round(sum(it.get("ahorro", 0) or 0 for it in detalle), 2)
    ahorro_descuento_extra = round(v.subtotal - v.total, 2)
    return {
        "id": v.id,'''
nuevo = '''    detalle = json.loads(v.detalle_json)
    ahorro_productos = round(sum(it.get("ahorro", 0) or 0 for it in detalle), 2)
    ahorro_descuento_extra = round(v.subtotal - v.total, 2)

    # Cuanto se ha devuelto ya de cada articulo (desde los registros negativos)
    _previas = db.query(Venta).filter(Venta.venta_origen_id == v.id).all()
    _ya_dev = {}
    for _d in _previas:
        for _it in json.loads(_d.detalle_json):
            _pid = _it.get("producto_id")
            _ya_dev[_pid] = _ya_dev.get(_pid, 0) + abs(_it.get("cantidad", 0))
    for _linea in detalle:
        _pid = _linea.get("producto_id")
        _dev = _ya_dev.get(_pid, 0)
        _linea["devuelto"] = round(_dev, 3)
        _linea["disponible_devolucion"] = round(_linea.get("cantidad", 0) - _dev, 3)

    return {
        "id": v.id,'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(MAIN, 'w', encoding='utf-8').write(src)
    res.append("OK main.py: detalle expone devuelto/disponible por articulo")
elif 'disponible_devolucion' in src:
    res.append("* main.py: ya exponia disponible_devolucion")
else:
    res.append("ERROR main.py: no se encontro obtener_venta")

# ============================================================
# 2 y 3. PANTALLA
# ============================================================
DEV = os.path.join(QA, 'static', 'devoluciones.html')
src = open(DEV, encoding='utf-8').read()

# --- 2a. Etiquetas de estado ---
viejo_et = "  const etiquetasEstado = {activa:'Activa', parcial:'Devolución parcial', cancelada:'Cancelada'};"
nuevo_et = "  const etiquetasEstado = {activa:'Activa', parcial:'Devolución parcial', devuelta:'Devuelta / Cancelada', cancelada:'Cancelada', devolucion:'Devolución'};"
if viejo_et in src:
    src = src.replace(viejo_et, nuevo_et, 1)
    res.append("OK pantalla: etiquetas de estado actualizadas")
elif "devuelta:'Devuelta" in src:
    res.append("* pantalla: etiquetas ya actualizadas")
else:
    res.append("ADVERTENCIA pantalla: no se encontraron las etiquetas de estado")

# --- 2b. Bloqueo de botones: el estado ahora es 'devuelta' ---
viejo_c = "  const cancelada = estado === 'cancelada';"
nuevo_c = "  const cancelada = (estado === 'devuelta' || estado === 'cancelada' || estado === 'devolucion');"
if viejo_c in src:
    src = src.replace(viejo_c, nuevo_c, 1)
    res.append("OK pantalla: botones se bloquean con estado 'devuelta'")
elif "estado === 'devuelta' ||" in src:
    res.append("* pantalla: el bloqueo ya contemplaba 'devuelta'")
else:
    res.append("ADVERTENCIA pantalla: no se encontro la variable cancelada")

# --- 2c. Usar devuelto/disponible que ahora manda el backend ---
viejo_d = "    const dev = yaDev[it.producto_id] || 0;\n    const disp = Math.round((it.cantidad - dev) * 1000) / 1000;"
nuevo_d = ("    const dev = (it.devuelto != null) ? it.devuelto : (yaDev[it.producto_id] || 0);\n"
           "    const disp = (it.disponible_devolucion != null) ? it.disponible_devolucion : Math.round((it.cantidad - dev) * 1000) / 1000;")
if viejo_d in src:
    src = src.replace(viejo_d, nuevo_d, 1)
    res.append("OK pantalla: usa las cantidades devueltas que manda el backend")
elif 'it.disponible_devolucion != null' in src:
    res.append("* pantalla: ya usaba disponible_devolucion")
else:
    res.append("ADVERTENCIA pantalla: no se encontro el calculo de dev/disp")

# --- 3. Botones del modal lado a lado ---
viejo_f = ".modal-footer button{width:100%;height:40px;border-radius:8px;background:var(--text);color:var(--bg2);border:none;font-size:14px;cursor:pointer;justify-content:center}"
nuevo_f = (".modal-footer{display:flex;justify-content:flex-end;gap:8px;margin-top:1.25rem}\n"
           ".modal-footer button{width:auto;min-width:96px;height:42px;padding:0 16px;border-radius:9px;border:0.5px solid var(--border);background:transparent;color:var(--text);font-size:14px;cursor:pointer}\n"
           ".modal-footer button.primary{background:var(--text);color:var(--bg2);border:none;font-weight:600}")
if viejo_f in src:
    src = src.replace(viejo_f, nuevo_f, 1)
    res.append("OK pantalla: botones del modal lado a lado, alineados a la derecha")
elif '.modal-footer{display:flex;justify-content:flex-end' in src:
    res.append("* pantalla: el pie del modal ya estaba corregido")
else:
    res.append("ADVERTENCIA pantalla: no se encontro la regla .modal-footer button")

open(DEV, 'w', encoding='utf-8').write(src)

# ============================================================
print()
for r in res:
    print(r)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves en devoluciones.html:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Prueba con Ctrl+Shift+R:")
    print("  - Devolver 1 de 3 -> debe mostrar '1 devuelto(s)' y dejar max 2")
    print("  - Devolver el resto -> botones deben quedar deshabilitados")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
