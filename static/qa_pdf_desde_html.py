#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Reemplaza generarPDFTicketVenta() por una version que reutiliza
el MISMO HTML que ya usa "Imprimir" (generarTicketHTML/ticketHTML),
convertido a PDF con jsPDF.html(). Esto garantiza que Descargar,
Imprimir y WhatsApp se vean identicos, ya que usan el mismo HTML/CSS.
Uso: cd ~/inventario-qa/static && python3 qa_pdf_desde_html.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

CSS_TICKET = (
    ".tk-line{display:flex;justify-content:space-between;margin-bottom:3px}"
    ".tk-total{font-weight:bold;font-size:15px;border-top:1px dashed #000;margin-top:6px;padding-top:6px}"
    ".tk-desc{color:#a32d2d}"
    ".tk-ahorro{color:#3b6d11;font-weight:bold}"
    ".tk-head,.tk-foot{text-align:center;margin:8px 0}"
    ".tk-negocio{font-size:18px;font-weight:bold}"
    ".tk-items{border-top:1px dashed #000;border-bottom:1px dashed #000;padding:6px 0;margin:6px 0}"
    ".tk-sub{font-size:12px;color:#000}"
)

# ================================================================
# PAGOS.HTML (usa generarTicketHTML)
# ================================================================
viejo_pagos = '''async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;
  const numItems = (v.detalle||[]).length;
  let alturaEstimada = 260 + numItems * 15;
  if(v.descuento_extra_pct>0) alturaEstimada += 36;
  const ahorroTk0 = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk0>0.005) alturaEstimada += 18;
  alturaEstimada = Math.max(alturaEstimada, 340);
  const doc = new jsPDFCtor({ unit:'pt', format:[320, alturaEstimada], orientation:'portrait' });
  const centerX = 160;
  let y = 24;
  try{
    const logoData = await cargarImagenBase64('/static/logo.png');
    const logoW = 80, logoH = 43;
    doc.addImage(logoData, 'PNG', centerX - logoW/2, y, logoW, logoH);
    y += logoH + 10;
  }catch(e){
    doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(20);
    doc.text('ONLY ENTERPRISES', centerX, y+10, {align:'center'});
    y += 26;
  }
  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(40);
  const fecha = new Date(v.fecha).toLocaleString('es-MX');
  if(v.sucursal){ doc.text('Sucursal '+v.sucursal, centerX, y, {align:'center'}); y+=13; }
  doc.text('Ticket de venta #'+v.id, centerX, y, {align:'center'}); y+=13;
  doc.text(fecha, centerX, y, {align:'center'}); y+=13;
  if(v.operador){ doc.text('Operador: '+v.operador, centerX, y, {align:'center'}); y+=13; }
  y+=6;
  doc.setDrawColor(220); doc.line(24,y,296,y); y+=16;
  doc.setFontSize(9);
  (v.detalle||[]).forEach(function(it){
    const cant = Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    doc.setTextColor(20);
    doc.text(cant+' '+it.nombre, 24, y, {maxWidth:190});
    doc.text(money(it.importe), 296, y, {align:'right'});
    y+=15;
  });
  y+=4;
  doc.line(24,y,296,y); y+=18;
  if(v.descuento_extra_pct>0){
    doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(20);
    doc.text('Subtotal', 24, y); doc.text(money(v.subtotal), 296, y, {align:'right'}); y+=15;
    doc.setTextColor(163,45,45);
    doc.text('Descuento '+v.descuento_extra_pct+'%', 24, y);
    doc.text('-'+money(v.subtotal*v.descuento_extra_pct/100), 296, y, {align:'right'}); y+=18;
  }
  const ahorroTk = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk>0.005){
    doc.setFont('helvetica','bold'); doc.setTextColor(59,109,17);
    doc.text('Ahorraste', 24, y); doc.text(money(ahorroTk), 296, y, {align:'right'}); y+=18;
  }
  doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(20);
  doc.text('TOTAL', 24, y); doc.text(money(v.total), 296, y, {align:'right'}); y+=22;
  doc.setDrawColor(220); doc.line(24,y,296,y); y+=18;
  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(20);
  if(v.metodo_pago==='credito'){
    doc.setTextColor(133,79,11);
    doc.text('Pago', 24, y); doc.text('A CRÉDITO', 296, y, {align:'right'}); y+=15;
    if(v.cliente_nombre){ doc.setTextColor(20); doc.text('Cliente', 24, y); doc.text(v.cliente_nombre, 296, y, {align:'right'}); y+=15; }
  } else if(v.metodo_pago==='tarjeta'){
    doc.text('Pago', 24, y); doc.text('TARJETA', 296, y, {align:'right'}); y+=15;
    if(v.tpv_terminal){ doc.text('Terminal', 24, y); doc.text(v.tpv_terminal, 296, y, {align:'right'}); y+=15; }
    if(v.tpv_referencia){ doc.text('Referencia', 24, y); doc.text(v.tpv_referencia, 296, y, {align:'right'}); y+=15; }
  } else {
    doc.text('Pago', 24, y); doc.text('EFECTIVO', 296, y, {align:'right'}); y+=15;
    if(v.pago_con!=null){
      doc.text('Pagó con', 24, y); doc.text(money(v.pago_con), 296, y, {align:'right'}); y+=15;
      doc.text('Cambio', 24, y); doc.text(money(v.cambio||0), 296, y, {align:'right'}); y+=15;
    }
  }
  y+=15;
  doc.setFont('helvetica','italic'); doc.setFontSize(9); doc.setTextColor(140);
  doc.text('Gracias por su compra', centerX, y, {align:'center'});
  return doc.output('blob');
}'''

nuevo_pagos = '''async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;
  const contenedor = document.createElement('div');
  contenedor.style.position = 'fixed';
  contenedor.style.left = '-9999px';
  contenedor.style.top = '0';
  contenedor.style.width = '300px';
  contenedor.style.background = '#ffffff';
  contenedor.style.padding = '16px';
  contenedor.style.fontFamily = 'monospace';
  contenedor.style.fontSize = '13px';
  contenedor.style.color = '#000000';
  contenedor.innerHTML = '<style>''' + CSS_TICKET + '''</style>' + generarTicketHTML(v);
  document.body.appendChild(contenedor);

  return new Promise(function(resolve){
    const doc = new jsPDFCtor({unit:'pt', format:[320, 700], orientation:'portrait'});
    doc.html(contenedor, {
      x: 10, y: 10,
      width: 300,
      windowWidth: 300,
      html2canvas: {scale: 2},
      callback: function(docFinal){
        document.body.removeChild(contenedor);
        resolve(docFinal.output('blob'));
      }
    });
  });
}'''

ruta_pagos = os.path.join(STATIC, 'pagos.html')
src = open(ruta_pagos, encoding='utf-8').read()
n1 = src.count(viejo_pagos)
if n1 == 1:
    src = src.replace(viejo_pagos, nuevo_pagos, 1)
    open(ruta_pagos, 'w', encoding='utf-8').write(src)
    print("OK pagos.html: generarPDFTicketVenta ahora reutiliza el HTML de Imprimir")
elif 'doc.html(contenedor' in src:
    print("* pagos.html: ya estaba actualizado")
else:
    print("ERROR pagos.html: no se encontro la funcion exacta (coincidencias: " + str(n1) + ")")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok1 = all(s.count('{') == s.count('}') for s in scripts)
print("   Balance de llaves en pagos.html:", "OK" if ok1 else "DESBALANCEADO")

# ================================================================
# HISTORIAL.HTML (usa ticketHTML en vez de generarTicketHTML)
# ================================================================
ruta_hist = os.path.join(STATIC, 'historial.html')
src2 = open(ruta_hist, encoding='utf-8').read()

viejo_hist = viejo_pagos  # misma logica original
nuevo_hist = nuevo_pagos.replace('generarTicketHTML(v)', 'ticketHTML(v)')

n2 = src2.count(viejo_hist)
if n2 == 1:
    src2 = src2.replace(viejo_hist, nuevo_hist, 1)
    open(ruta_hist, 'w', encoding='utf-8').write(src2)
    print("OK historial.html: generarPDFTicketVenta ahora reutiliza el HTML de Imprimir")
elif 'doc.html(contenedor' in src2:
    print("* historial.html: ya estaba actualizado")
else:
    print("ERROR historial.html: no se encontro la funcion exacta (coincidencias: " + str(n2) + ")")

scripts2 = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src2, re.DOTALL)
ok2 = all(s.count('{') == s.count('}') for s in scripts2)
print("   Balance de llaves en historial.html:", "OK" if ok2 else "DESBALANCEADO")

print()
print("=" * 55)
if ok1 and ok2:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Descargar y WhatsApp ahora generan el PDF a partir del")
    print("mismo HTML que usa Imprimir -- deberian verse identicos.")
else:
    print("ADVERTENCIA: desbalance de llaves en algun archivo. NO se reinicio el servicio.")
