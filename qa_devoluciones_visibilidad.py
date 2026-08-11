#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Tres mejoras de visibilidad en devoluciones:
 1. El registro negativo guarda el descuento general de la venta
    original, para que el ticket muestre Subtotal / Descuento / TOTAL
    y se entienda por que se devolvio menos que el precio de lista.
 2. Dashboard: tarjeta con el total devuelto y cuantos movimientos.
 3. Reporte PDF: linea de devoluciones con total y numero de movimientos.
Uso: cd ~/inventario-qa && python3 qa_devoluciones_visibilidad.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
res = []

# ============================================================
# 1. BACKEND: guardar subtotal bruto + descuento en el registro
# ============================================================
MAIN = os.path.join(QA, 'main.py')
src = open(MAIN, encoding='utf-8').read()

# --- devolver_items ---
viejo = '''    monto_total = round(monto_total, 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-monto_total,
        descuento_extra_pct=0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    total_items = sum(x.get("cantidad", 0) for x in detalle)'''
nuevo = '''    monto_total = round(monto_total, 2)
    subtotal_bruto = round(sum(abs(x["cantidad"]) * x["precio_unitario"] for x in detalle_dev), 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-subtotal_bruto,
        descuento_extra_pct=v.descuento_extra_pct or 0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    total_items = sum(x.get("cantidad", 0) for x in detalle)'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK devolucion: guarda subtotal bruto y descuento general")
elif 'subtotal_bruto = round(sum(abs(x["cantidad"])' in src:
    res.append("* devolucion: ya guardaba el descuento")
else:
    res.append("ERROR: no se encontro el bloque Venta() de devolver_items")

# --- cancelar_venta ---
viejo2 = '''    monto_total = round(monto_total, 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-monto_total,
        descuento_extra_pct=0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    v.estado = "devuelta"'''
nuevo2 = '''    monto_total = round(monto_total, 2)
    subtotal_bruto = round(sum(abs(x["cantidad"]) * x["precio_unitario"] for x in detalle_dev), 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-subtotal_bruto,
        descuento_extra_pct=v.descuento_extra_pct or 0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    v.estado = "devuelta"'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    res.append("OK cancelacion: guarda subtotal bruto y descuento general")
elif src.count('subtotal_bruto = round(sum(abs(x["cantidad"])') >= 2:
    res.append("* cancelacion: ya guardaba el descuento")
else:
    res.append("ERROR: no se encontro el bloque Venta() de cancelar_venta")

# --- Dashboard: agregar devoluciones al resumen ---
viejo3 = '''    actual["gastos"] = gastos_total
    actual["ganancia_neta"] = round(actual["ganancia"] - gastos_total, 2)'''
nuevo3 = '''    actual["gastos"] = gastos_total
    actual["ganancia_neta"] = round(actual["ganancia"] - gastos_total, 2)

    # Devoluciones del periodo (registros con total negativo)
    dev_q = db.query(Venta).filter(Venta.total < 0)
    if d:
        dev_q = dev_q.filter(Venta.creado_en >= d)
    _devs = dev_q.all()
    actual["devoluciones_total"] = round(sum(abs(x.total) for x in _devs), 2)
    actual["devoluciones_num"] = len(_devs)'''
if viejo3 in src:
    src = src.replace(viejo3, nuevo3, 1)
    res.append("OK dashboard: expone devoluciones_total y devoluciones_num")
elif 'devoluciones_total' in src:
    res.append("* dashboard: ya exponia devoluciones")
else:
    res.append("ADVERTENCIA: no se encontro el bloque de gastos del dashboard")

# --- Reporte: agregar devoluciones ---
viejo4 = '''    ganancia_neta = round(total_vendido - gastos_total, 2)'''
nuevo4 = '''    ganancia_neta = round(total_vendido - gastos_total, 2)

    _devs = [x for x in ventas if x.total < 0]
    devoluciones_total = round(sum(abs(x.total) for x in _devs), 2)
    devoluciones_num = len(_devs)'''
if viejo4 in src:
    src = src.replace(viejo4, nuevo4, 1)
    res.append("OK reporte: calcula devoluciones del periodo")
elif 'devoluciones_num = len(_devs)' in src:
    res.append("* reporte: ya calculaba devoluciones")

viejo5 = '''        "gastos": gastos_total,
        "num_gastos": len(gastos_lista),'''
nuevo5 = '''        "gastos": gastos_total,
        "num_gastos": len(gastos_lista),
        "devoluciones_total": devoluciones_total,
        "devoluciones_num": devoluciones_num,'''
if viejo5 in src:
    src = src.replace(viejo5, nuevo5, 1)
    res.append("OK reporte: expone devoluciones en la respuesta")

open(MAIN, 'w', encoding='utf-8').write(src)

# ============================================================
# 2. TICKET: que el descuento se lea bien con montos negativos
# ============================================================
viejo_t = "<span>-${money(v.subtotal*v.descuento_extra_pct/100)}</span>"
nuevo_t = "<span>${money(-(v.subtotal*v.descuento_extra_pct/100))}</span>"
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(QA, 'static', nombre)
    s = open(ruta, encoding='utf-8').read()
    if viejo_t in s:
        s = s.replace(viejo_t, nuevo_t)
        open(ruta, 'w', encoding='utf-8').write(s)
        res.append("OK " + nombre + ": el descuento se muestra con el signo correcto")
    elif nuevo_t in s:
        res.append("* " + nombre + ": ya estaba corregido")
    else:
        res.append("ADVERTENCIA " + nombre + ": no se encontro la linea del descuento")

# ============================================================
# 3. DASHBOARD: tarjeta de devoluciones
# ============================================================
ruta = os.path.join(QA, 'static', 'dashboard.html')
s = open(ruta, encoding='utf-8').read()

viejo_card = '''    <div class="stat-card">
      <div class="stat-icon">💸</div>
      <div class="stat-label">Gastos</div>
      <div class="stat-value red" id="st-gastos">—</div>
      <div class="stat-delta">&nbsp;</div>
    </div>'''
nuevo_card = '''    <div class="stat-card">
      <div class="stat-icon">💸</div>
      <div class="stat-label">Gastos</div>
      <div class="stat-value red" id="st-gastos">—</div>
      <div class="stat-delta">&nbsp;</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">↩️</div>
      <div class="stat-label">Devoluciones</div>
      <div class="stat-value red" id="st-devoluciones">—</div>
      <div class="stat-delta" id="st-devoluciones-num">&nbsp;</div>
    </div>'''
if viejo_card in s:
    s = s.replace(viejo_card, nuevo_card, 1)
    res.append("OK dashboard.html: tarjeta de devoluciones agregada")
elif 'st-devoluciones' in s:
    res.append("* dashboard.html: la tarjeta ya existia")
else:
    res.append("ADVERTENCIA dashboard.html: no se encontro la tarjeta de gastos")

viejo_js = "      document.getElementById('st-gastos').textContent = money(d.gastos);"
nuevo_js = '''      document.getElementById('st-gastos').textContent = money(d.gastos);
      const _dv = document.getElementById('st-devoluciones');
      if(_dv){
        _dv.textContent = d.devoluciones_total ? '-' + money(d.devoluciones_total) : money(0);
        const _dn = document.getElementById('st-devoluciones-num');
        if(_dn) _dn.textContent = (d.devoluciones_num || 0) + ' movimiento(s)';
      }'''
if viejo_js in s:
    s = s.replace(viejo_js, nuevo_js, 1)
    res.append("OK dashboard.html: la tarjeta se llena con los datos")
elif "st-devoluciones')" in s and "_dv.textContent" in s:
    res.append("* dashboard.html: el JS ya estaba")
else:
    res.append("ADVERTENCIA dashboard.html: no se encontro la asignacion de st-gastos")

open(ruta, 'w', encoding='utf-8').write(s)

# ============================================================
# 4. REPORTE PDF: linea de devoluciones
# ============================================================
viejo_pdf = """  fila('Gastos (' + (d.num_gastos || 0) + ')', '-' + money(d.gastos));"""
nuevo_pdf = """  fila('Gastos (' + (d.num_gastos || 0) + ')', '-' + money(d.gastos));
  if(d.devoluciones_num){
    fila('Devoluciones (' + d.devoluciones_num + ')', '-' + money(d.devoluciones_total));
  }"""
for nombre in ['historial.html', 'dashboard.html']:
    ruta = os.path.join(QA, 'static', nombre)
    s = open(ruta, encoding='utf-8').read()
    if viejo_pdf in s:
        s = s.replace(viejo_pdf, nuevo_pdf, 1)
        open(ruta, 'w', encoding='utf-8').write(s)
        res.append("OK " + nombre + ": reporte PDF incluye devoluciones")
    elif "d.devoluciones_num){" in s:
        res.append("* " + nombre + ": el reporte ya incluia devoluciones")
    else:
        res.append("ADVERTENCIA " + nombre + ": no se encontro la linea de gastos del PDF")

# ============================================================
print()
for r in res:
    print(r)

ok_total = True
print()
for nombre in ['pagos.html', 'historial.html', 'dashboard.html']:
    s = open(os.path.join(QA, 'static', nombre), encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 58)
if ok_total and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. NOTA: las devoluciones YA hechas seguiran sin mostrar el")
    print("descuento (se guardaron sin el). Haz una devolucion nueva para probar.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
