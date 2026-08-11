#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Reemplaza generarReportePDF por una version que dibuja el PDF
directamente con jsPDF (texto nativo), en vez de capturar HTML con
html2canvas. Mas confiable: sin recortes ni problemas de opacidad.
Uso: cd ~/inventario-qa/static && python3 qa_reporte_pdf_nativo.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

NUEVA_FUNCION = '''async function generarReportePDF(desdeISO, hastaISO, etiquetaPeriodo){
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
  const jsPDFCtor = window.jspdf.jsPDF;
  const W = 595, M = 40, RIGHT = W - M;
  const doc = new jsPDFCtor({unit:'pt', format:'a4', orientation:'portrait'});
  let y = 40;

  function linea(){
    doc.setDrawColor(0);
    doc.setLineDashPattern([3, 2], 0);
    doc.line(M, y, RIGHT, y);
    doc.setLineDashPattern([], 0);
    y += 18;
  }
  function fila(etiqueta, valor, bold, size){
    doc.setFont('courier', bold ? 'bold' : 'normal');
    doc.setFontSize(size || 10);
    doc.setTextColor(0);
    doc.text(String(etiqueta), M, y);
    doc.text(String(valor), RIGHT, y, {align:'right'});
    y += (size || 10) + 6;
  }
  function titulo(txt){
    doc.setFont('courier','bold'); doc.setFontSize(12); doc.setTextColor(0);
    doc.text(txt, M, y);
    y += 20;
  }

  try{
    const logoData = await cargarImagenBase64('/static/logo.png');
    const lw = 110, lh = 59;
    doc.addImage(logoData, 'PNG', (W - lw)/2, y, lw, lh);
    y += lh + 14;
  }catch(e){
    doc.setFont('courier','bold'); doc.setFontSize(15); doc.setTextColor(0);
    doc.text('ONLY ENTERPRISES', W/2, y + 12, {align:'center'});
    y += 32;
  }

  doc.setFont('courier','bold'); doc.setFontSize(15); doc.setTextColor(0);
  doc.text('Reporte de ventas', W/2, y, {align:'center'}); y += 18;
  doc.setFont('courier','normal'); doc.setFontSize(10);
  doc.text(etiquetaPeriodo || '', W/2, y, {align:'center'}); y += 14;
  doc.setFontSize(9);
  doc.text('Generado: ' + new Date().toLocaleString('es-MX').replace(',',''), W/2, y, {align:'center'});
  y += 18;
  linea();

  titulo('Resumen');
  fila('Ventas totales (' + d.num_ventas + ' ventas)', money(d.total_vendido));
  fila('Gastos (' + (d.num_gastos || 0) + ')', '-' + money(d.gastos));
  fila('Ganancia después de gastos', money(d.ganancia_neta), true, 12);
  fila('Cuentas por cobrar', money(d.total_por_cobrar));
  y += 6;
  linea();

  titulo('Métodos de pago');
  if(!d.desglose_metodos_pago.length){
    doc.setFont('courier','normal'); doc.setFontSize(10);
    doc.text('Sin ventas en el período', M, y); y += 16;
  }else{
    d.desglose_metodos_pago.forEach(function(m){
      fila((nombresMetodo[m.metodo] || m.metodo) + ' (' + m.cantidad + ')', money(m.total));
    });
  }
  y += 6;
  linea();

  titulo('Clientes a crédito');
  if(!d.clientes_detalle.length){
    doc.setFont('courier','normal'); doc.setFontSize(10);
    doc.text('Sin movimientos de crédito en el período', M, y); y += 16;
  }else{
    const c1 = M, c2 = M + 200, c3 = M + 310, c4 = RIGHT;
    doc.setFont('courier','bold'); doc.setFontSize(9); doc.setTextColor(0);
    doc.text('Cliente', c1, y);
    doc.text('Ventas créd.', c2, y, {align:'right'});
    doc.text('Pagos', c3, y, {align:'right'});
    doc.text('Saldo', c4, y, {align:'right'});
    y += 14;
    doc.setFont('courier','normal');
    d.clientes_detalle.forEach(function(c){
      if(y > 780){ doc.addPage(); y = 50; }
      const nombreCorto = doc.splitTextToSize(c.nombre, 190)[0];
      doc.setFont('courier','normal'); doc.setFontSize(9);
      doc.text(nombreCorto, c1, y);
      doc.text(money(c.ventas_credito_periodo), c2, y, {align:'right'});
      doc.text(money(c.pagos_periodo), c3, y, {align:'right'});
      doc.setFont('courier','bold');
      doc.text(money(c.saldo_actual), c4, y, {align:'right'});
      y += 14;
    });
  }

  const blob = doc.output('blob');
  const urlBlob = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = urlBlob; a.download = 'reporte_' + new Date().toISOString().slice(0,10) + '.pdf';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(urlBlob); }, 3000);
}'''

for nombre in ['historial.html', 'dashboard.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()

    inicio = src.find('async function generarReportePDF(desdeISO, hastaISO, etiquetaPeriodo){')
    if inicio == -1:
        print("ERROR " + nombre + ": no se encontro generarReportePDF")
        continue

    profundidad = 0
    encontrado = False
    fin = -1
    for idx in range(inicio, len(src)):
        c = src[idx]
        if c == '{':
            profundidad += 1
            encontrado = True
        elif c == '}':
            profundidad -= 1
            if encontrado and profundidad == 0:
                fin = idx + 1
                break

    if fin == -1:
        print("ERROR " + nombre + ": no se pudo determinar el cierre")
        continue

    src = src[:inicio] + NUEVA_FUNCION + src[fin:]

    # dashboard.html necesita cargarImagenBase64 (historial ya la tiene)
    if nombre == 'dashboard.html' and 'function cargarImagenBase64' not in src:
        helper = '''let _logoCacheDataUrl = null;
function cargarImagenBase64(url){
  if(_logoCacheDataUrl) return Promise.resolve(_logoCacheDataUrl);
  return new Promise(function(resolve, reject){
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function(){
      const canvas = document.createElement('canvas');
      const escala = 240 / img.width;
      canvas.width = 240;
      canvas.height = Math.round(img.height * escala);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      _logoCacheDataUrl = canvas.toDataURL('image/png');
      resolve(_logoCacheDataUrl);
    };
    img.onerror = reject;
    img.src = url;
  });
}

'''
        src = src.replace('async function generarReportePDF', helper + 'async function generarReportePDF', 1)
        print("OK dashboard.html: helper cargarImagenBase64 agregado")

    open(ruta, 'w', encoding='utf-8').write(src)
    print("OK " + nombre + ": generarReportePDF reemplazada (PDF nativo, sin html2canvas)")

print()
ok_total = True
for nombre in ['historial.html', 'dashboard.html']:
    ruta = os.path.join(STATIC, nombre)
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 55)
if ok_total:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El reporte ahora se dibuja directo con jsPDF (hoja A4),")
    print("sin capturas de imagen. Genera de nuevo con Ctrl+Shift+R.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
