#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] SCRIPT UNICO. Hace todo de una vez:
 1. Backend: endpoint /api/reporte-completo
 2. Historial: boton "Reporte" + generacion del PDF (usa el rango del filtro)
 3. Dashboard: boton "Reporte" + generacion del PDF (usa el periodo activo)
 4. Punto de venta: quita la restriccion del monto de pago (vacio = pago exacto)
Uso: cd ~/inventario-qa && python3 qa_reporte_completo_todo.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')
resultados = []

# ============================================================
# 1. BACKEND
# ============================================================
MAIN = os.path.join(QA, 'main.py')
src = open(MAIN, encoding='utf-8').read()

if '/api/reporte-completo' in src:
    resultados.append("* backend: el endpoint ya existia")
else:
    marcador = '@app.get("/api/clientes-resumen")'
    if marcador not in src:
        resultados.append("ERROR backend: no se encontro el marcador")
    else:
        endpoint = '''@app.get("/api/reporte-completo")
def reporte_completo(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)

    ventas_q = db.query(Venta)
    if d:
        ventas_q = ventas_q.filter(Venta.creado_en >= d)
    if h:
        ventas_q = ventas_q.filter(Venta.creado_en <= h)
    ventas = ventas_q.all()

    total_vendido = round(sum(v.total for v in ventas), 2)

    por_metodo = {}
    for v in ventas:
        m = v.metodo_pago or "efectivo"
        if m not in por_metodo:
            por_metodo[m] = {"cantidad": 0, "total": 0.0}
        por_metodo[m]["cantidad"] += 1
        por_metodo[m]["total"] += v.total
    desglose_metodos = sorted(
        [{"metodo": k, "cantidad": v["cantidad"], "total": round(v["total"], 2)} for k, v in por_metodo.items()],
        key=lambda x: x["total"], reverse=True
    )

    gastos_q = db.query(Gasto)
    if d:
        gastos_q = gastos_q.filter(Gasto.fecha >= d)
    if h:
        gastos_q = gastos_q.filter(Gasto.fecha <= h)
    gastos_lista = gastos_q.all()
    gastos_total = round(sum(g.monto for g in gastos_lista), 2)

    ganancia_neta = round(total_vendido - gastos_total, 2)

    clientes = db.query(Cliente).all()
    detalle_clientes = []
    for c in clientes:
        saldo = _saldo_cliente(db, c.id)
        ventas_credito_periodo = [v for v in ventas if v.cliente_id == c.id and v.metodo_pago == "credito"]
        monto_ventas_credito = round(sum(v.total for v in ventas_credito_periodo), 2)
        pagos_q = db.query(PagoCredito).filter(PagoCredito.cliente_id == c.id)
        if d:
            pagos_q = pagos_q.filter(PagoCredito.creado_en >= d)
        if h:
            pagos_q = pagos_q.filter(PagoCredito.creado_en <= h)
        monto_pagos_periodo = round(sum(p.monto for p in pagos_q.all()), 2)

        if saldo > 0 or monto_ventas_credito > 0 or monto_pagos_periodo > 0:
            detalle_clientes.append({
                "cliente_id": c.id,
                "nombre": c.nombre,
                "saldo_actual": round(saldo, 2),
                "ventas_credito_periodo": monto_ventas_credito,
                "pagos_periodo": monto_pagos_periodo,
            })
    detalle_clientes = sorted(detalle_clientes, key=lambda x: x["saldo_actual"], reverse=True)

    return {
        "desde": desde,
        "hasta": hasta,
        "total_vendido": total_vendido,
        "num_ventas": len(ventas),
        "gastos": gastos_total,
        "num_gastos": len(gastos_lista),
        "ganancia_neta": ganancia_neta,
        "desglose_metodos_pago": desglose_metodos,
        "clientes_detalle": detalle_clientes,
        "total_por_cobrar": round(sum(c["saldo_actual"] for c in detalle_clientes if c["saldo_actual"] > 0), 2),
    }


'''
        src = src.replace(marcador, endpoint + marcador, 1)
        open(MAIN, 'w', encoding='utf-8').write(src)
        resultados.append("OK backend: endpoint /api/reporte-completo agregado")

# ============================================================
# JS compartido del PDF (se inserta en ambas paginas)
# ============================================================
JS_PDF = '''
// ─── Reporte completo en PDF ────────────────────────────────────────────
async function generarReportePDF(desdeISO, hastaISO, etiquetaPeriodo){
  let params = [];
  if(desdeISO) params.push('desde=' + encodeURIComponent(desdeISO));
  if(hastaISO) params.push('hasta=' + encodeURIComponent(hastaISO));
  const url = '/api/reporte-completo' + (params.length ? '?' + params.join('&') : '');

  let d;
  try{
    const r = await authFetch(url);
    if(!r.ok){ alert('No se pudo generar el reporte'); return; }
    d = await r.json();
  }catch(e){ alert('Error de conexión al generar el reporte'); return; }

  const nombresMetodo = {efectivo:'Efectivo', tarjeta:'Tarjeta', credito:'Crédito', transferencia:'Transferencia'};

  const cont = document.createElement('div');
  cont.style.position='absolute'; cont.style.left='-9999px'; cont.style.top='0';
  cont.style.width='700px'; cont.style.background='#ffffff'; cont.style.padding='28px 32px';
  cont.style.fontFamily='monospace'; cont.style.fontSize='13px'; cont.style.color='#000000';

  const RAYA = '<div style="border-top:1px dashed #000;margin:12px 0"></div>';
  let html = '<div style="text-align:center;margin-bottom:6px">'
    + '<img src="' + (typeof _logoCacheDataUrl!=='undefined' && _logoCacheDataUrl ? _logoCacheDataUrl : '/static/logo.png') + '" style="height:52px;width:auto">'
    + '<div style="font-size:16px;font-weight:bold;margin-top:6px">Reporte de ventas</div>'
    + '<div style="font-size:12px">' + (etiquetaPeriodo||'') + '</div>'
    + '<div style="font-size:11px">Generado: ' + new Date().toLocaleString('es-MX').replace(',','') + '</div>'
    + '</div>' + RAYA;

  html += '<div style="font-weight:bold;font-size:14px;margin-bottom:8px">Resumen</div>';
  const fila = (a,b,bold)=> '<div style="display:flex;justify-content:space-between;margin-bottom:4px'
    + (bold?';font-weight:bold;font-size:14px':'') + '"><span>'+a+'</span><span>'+b+'</span></div>';
  html += fila('Ventas totales (' + d.num_ventas + ' ventas)', money(d.total_vendido));
  html += fila('Gastos (' + (d.num_gastos||0) + ')', '-' + money(d.gastos));
  html += fila('Ganancia después de gastos', money(d.ganancia_neta), true);
  html += fila('Cuentas por cobrar', money(d.total_por_cobrar));
  html += RAYA;

  html += '<div style="font-weight:bold;font-size:14px;margin-bottom:8px">Métodos de pago</div>';
  if(!d.desglose_metodos_pago.length){
    html += '<div style="margin-bottom:4px">Sin ventas en el período</div>';
  }else{
    d.desglose_metodos_pago.forEach(function(m){
      html += fila((nombresMetodo[m.metodo]||m.metodo) + ' (' + m.cantidad + ')', money(m.total));
    });
  }
  html += RAYA;

  html += '<div style="font-weight:bold;font-size:14px;margin-bottom:8px">Clientes a crédito</div>';
  if(!d.clientes_detalle.length){
    html += '<div>Sin movimientos de crédito en el período</div>';
  }else{
    html += '<div style="display:flex;justify-content:space-between;font-weight:bold;margin-bottom:6px;font-size:12px">'
      + '<span style="flex:2">Cliente</span><span style="flex:1;text-align:right">Ventas créd.</span>'
      + '<span style="flex:1;text-align:right">Pagos</span><span style="flex:1;text-align:right">Saldo</span></div>';
    d.clientes_detalle.forEach(function(c){
      html += '<div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px">'
        + '<span style="flex:2">' + c.nombre + '</span>'
        + '<span style="flex:1;text-align:right">' + money(c.ventas_credito_periodo) + '</span>'
        + '<span style="flex:1;text-align:right">' + money(c.pagos_periodo) + '</span>'
        + '<span style="flex:1;text-align:right;font-weight:bold">' + money(c.saldo_actual) + '</span></div>';
    });
  }

  cont.innerHTML = html;
  document.body.appendChild(cont);
  try{
    await new Promise(function(r){ setTimeout(r, 90); });
    const canvas = await html2canvas(cont, {scale:2, backgroundColor:'#ffffff', useCORS:true});
    const imgData = canvas.toDataURL('image/png');
    const jsPDFCtor = window.jspdf.jsPDF;
    const pdfW = 595;
    const pdfH = (canvas.height * pdfW) / canvas.width;
    const doc = new jsPDFCtor({unit:'pt', format:[pdfW, pdfH], orientation:'portrait'});
    doc.addImage(imgData, 'PNG', 0, 0, pdfW, pdfH);
    const blob = doc.output('blob');
    const urlBlob = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = urlBlob; a.download = 'reporte_' + new Date().toISOString().slice(0,10) + '.pdf';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function(){ URL.revokeObjectURL(urlBlob); }, 3000);
  }catch(e){
    alert('Error al generar el PDF');
  }finally{
    document.body.removeChild(cont);
  }
}
'''

TAGS_LIBS = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>\n'
             '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>')

# ============================================================
# 2. HISTORIAL
# ============================================================
HIST = os.path.join(QA, 'static', 'historial.html')
src = open(HIST, encoding='utf-8').read()
original = src

viejo_topbar = '''  <div class="topbar-right">
    <a href="/pagos" class="btn-inicio" style="min-width:0">💳 Vender</a>
  </div>'''
nuevo_topbar = '''  <div class="topbar-right">
    <button class="icon-btn" onclick="reporteDesdeHistorial()" title="Descargar reporte PDF" style="margin-right:6px">📄</button>
    <a href="/pagos" class="btn-inicio" style="min-width:0">💳 Vender</a>
  </div>'''
if viejo_topbar in src:
    src = src.replace(viejo_topbar, nuevo_topbar, 1)
    resultados.append("OK historial: boton de reporte agregado")
elif 'reporteDesdeHistorial()' in src:
    resultados.append("* historial: el boton ya existia")
else:
    resultados.append("ERROR historial: no se encontro el topbar")

if 'function reporteDesdeHistorial' not in src:
    fn = JS_PDF + '''
function reporteDesdeHistorial(){
  const dStr = document.getElementById('f-desde').value;
  const hStr = document.getElementById('f-hasta').value;
  let desdeISO=null, hastaISO=null, etiqueta='Todo el histórico';
  if(dStr){ desdeISO = new Date(dStr+'T00:00:00').toISOString(); }
  if(hStr){ hastaISO = new Date(hStr+'T23:59:59.999').toISOString(); }
  if(dStr && hStr) etiqueta = dStr==hStr ? dStr : (dStr + ' a ' + hStr);
  else if(dStr) etiqueta = 'Desde ' + dStr;
  else if(hStr) etiqueta = 'Hasta ' + hStr;
  generarReportePDF(desdeISO, hastaISO, etiqueta);
}
'''
    m = re.search(r'</script>\s*</body>', src)
    if m:
        src = src[:m.start()] + fn + src[m.start():]
        resultados.append("OK historial: funciones del reporte agregadas")
    else:
        resultados.append("ERROR historial: no se encontro el cierre de script")

if src != original:
    open(HIST, 'w', encoding='utf-8').write(src)

# ============================================================
# 3. DASHBOARD
# ============================================================
DASH = os.path.join(QA, 'static', 'dashboard.html')
src = open(DASH, encoding='utf-8').read()
original = src

if 'jspdf.umd.min.js' not in src:
    if '<script src="/static/auth.js"></script>' in src:
        src = src.replace('<script src="/static/auth.js"></script>',
                          TAGS_LIBS + '\n<script src="/static/auth.js"></script>', 1)
        resultados.append("OK dashboard: librerias jsPDF/html2canvas agregadas")
    else:
        resultados.append("ERROR dashboard: no se encontro el script de auth.js")
else:
    resultados.append("* dashboard: librerias ya estaban")

viejo_dash_topbar = '''    <button class="icon-btn" onclick="cargarTodo();cargarSerie();" title="Actualizar">↻</button>'''
nuevo_dash_topbar = '''    <button class="icon-btn" onclick="reporteDesdeDashboard()" title="Descargar reporte PDF" style="margin-right:6px">📄</button>
    <button class="icon-btn" onclick="cargarTodo();cargarSerie();" title="Actualizar">↻</button>'''
if viejo_dash_topbar in src:
    src = src.replace(viejo_dash_topbar, nuevo_dash_topbar, 1)
    resultados.append("OK dashboard: boton de reporte agregado")
elif 'reporteDesdeDashboard()' in src:
    resultados.append("* dashboard: el boton ya existia")
else:
    resultados.append("ERROR dashboard: no se encontro el topbar")

if 'function reporteDesdeDashboard' not in src:
    fn = JS_PDF + '''
function reporteDesdeDashboard(){
  const desdeISO = limitesPeriodo(periodoActual);
  const etiquetas = {hoy:'Hoy', semana:'Esta semana', mes:'Este mes', todo:'Todo el histórico'};
  generarReportePDF(desdeISO, null, etiquetas[periodoActual] || '');
}
'''
    m = re.search(r'</script>\s*</body>', src)
    if m:
        src = src[:m.start()] + fn + src[m.start():]
        resultados.append("OK dashboard: funciones del reporte agregadas")
    else:
        resultados.append("ERROR dashboard: no se encontro el cierre de script")

if src != original:
    open(DASH, 'w', encoding='utf-8').write(src)

# ============================================================
# 4. PAGOS: quitar restriccion del monto
# ============================================================
PAGOS = os.path.join(QA, 'static', 'pagos.html')
src = open(PAGOS, encoding='utf-8').read()

viejo_pago = '''  if(metodoPago==='efectivo'){
    const pagoRaw=document.getElementById('c-pago').value.trim();
    if(pagoRaw===''){
      msg.className='msg error show';msg.textContent='Ingresa con cuánto paga el cliente';
      document.getElementById('c-pago').focus();return;
    }
    const pago=parseFloat(pagoRaw);
    if(isNaN(pago)||pago<0){msg.className='msg error show';msg.textContent='Monto de pago inválido';return;}
    if(pago<total){msg.className='msg error show';msg.textContent=`El pago (${money(pago)}) es menor al total (${money(total)})`;return;}
    body.pago_con=pago;
  }else if(metodoPago==='tarjeta'){'''
nuevo_pago = '''  if(metodoPago==='efectivo'){
    const pagoRaw=document.getElementById('c-pago').value.trim();
    if(pagoRaw===''){
      body.pago_con=total;
    }else{
      const pago=parseFloat(pagoRaw);
      if(isNaN(pago)||pago<0){msg.className='msg error show';msg.textContent='Monto de pago inválido';return;}
      if(pago<total){msg.className='msg error show';msg.textContent=`El pago (${money(pago)}) es menor al total (${money(total)})`;return;}
      body.pago_con=pago;
    }
  }else if(metodoPago==='tarjeta'){'''
if viejo_pago in src:
    src = src.replace(viejo_pago, nuevo_pago, 1)
    open(PAGOS, 'w', encoding='utf-8').write(src)
    resultados.append("OK pagos: monto de pago ya no es obligatorio (vacio = exacto)")
elif "body.pago_con=total;\n    }else{" in src:
    resultados.append("* pagos: ya estaba corregido")
else:
    resultados.append("ERROR pagos: no se encontro el bloque del monto")

# ============================================================
# RESULTADOS Y VERIFICACION
# ============================================================
print()
for r in resultados:
    print(r)

print()
ok_total = True
for f in ['historial.html', 'dashboard.html', 'pagos.html']:
    ruta = os.path.join(QA, 'static', f)
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + f + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 55)
if ok_total and not any(r.startswith('ERROR') for r in resultados):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Prueba con Ctrl+Shift+R:")
    print("  - Historial: boton 📄 (usa el rango del filtro Desde/Hasta)")
    print("  - Dashboard: boton 📄 (usa la pestana de periodo activa)")
    print("  - Punto de venta: cobrar dejando vacio el campo de pago")
else:
    print("ADVERTENCIA: hubo errores o desbalance. NO se reinicio el servicio.")
    print("Revisa los mensajes de arriba.")
