#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Revierte al dibujado manual de jsPDF (mas confiable que html2canvas,
que no soporta bien bordes punteados ni variables CSS), y esta vez agrega
lineas PUNTEADAS de verdad usando el soporte nativo de jsPDF.
Uso: cd ~/inventario-qa/static && python3 qa_pdf_lineas_punteadas.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo_html_version = '''async function generarPDFTicketVenta(v){
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
  contenedor.style.color = '#000000';'''

nueva_funcion_completa = '''async function generarPDFTicketVenta(v){
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

  function lineaPunteada(y1){
    doc.setDrawColor(0);
    doc.setLineDashPattern([2, 1.5], 0);
    doc.line(24, y1, 296, y1);
    doc.setLineDashPattern([], 0);
  }

  try{
    const logoData = await cargarImagenBase64('/static/logo.png');
    const logoW = 80, logoH = 43;
    doc.addImage(logoData, 'PNG', centerX - logoW/2, y, logoW, logoH);
    y += logoH + 10;
  }catch(e){
    doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(0);
    doc.text('ONLY ENTERPRISES', centerX, y+10, {align:'center'});
    y += 26;
  }
  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(0);
  const fecha = new Date(v.fecha).toLocaleString('es-MX');
  if(v.sucursal){ doc.text('Sucursal '+v.sucursal, centerX, y, {align:'center'}); y+=13; }
  doc.text('Ticket de venta #'+v.id, centerX, y, {align:'center'}); y+=13;
  doc.text(fecha, centerX, y, {align:'center'}); y+=13;
  if(v.operador){ doc.text('Operador: '+v.operador, centerX, y, {align:'center'}); y+=13; }
  y+=8;
  lineaPunteada(y); y+=16;
  doc.setFontSize(9);
  (v.detalle||[]).forEach(function(it){
    const cant = Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    doc.setTextColor(0);
    doc.text(cant+' '+it.nombre, 24, y, {maxWidth:190});
    doc.text(money(it.importe), 296, y, {align:'right'});
    y+=15;
  });
  y+=4;
  lineaPunteada(y); y+=18;
  if(v.descuento_extra_pct>0){
    doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(0);
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
  doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(0);
  doc.text('TOTAL', 24, y); doc.text(money(v.total), 296, y, {align:'right'}); y+=22;
  lineaPunteada(y); y+=18;
  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(0);
  if(v.metodo_pago==='credito'){
    doc.setTextColor(133,79,11);
    doc.text('Pago', 24, y); doc.text('A CRÉDITO', 296, y, {align:'right'}); y+=15;
    if(v.cliente_nombre){ doc.setTextColor(0); doc.text('Cliente', 24, y); doc.text(v.cliente_nombre, 296, y, {align:'right'}); y+=15; }
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
  doc.setFont('helvetica','italic'); doc.setFontSize(9); doc.setTextColor(90);
  doc.text('Gracias por su compra', centerX, y, {align:'center'});
  return doc.output('blob');
}'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()

    # Encontrar la funcion completa actual (version html2canvas) por rango
    inicio = src.find('async function generarPDFTicketVenta(v){')
    if inicio == -1:
        print("ERROR " + nombre + ": no se encontro generarPDFTicketVenta")
        continue

    # Buscar el cierre correcto contando llaves desde el inicio de la funcion
    profundidad = 0
    i = inicio
    encontrado_inicio_llave = False
    fin = -1
    for idx in range(inicio, len(src)):
        c = src[idx]
        if c == '{':
            profundidad += 1
            encontrado_inicio_llave = True
        elif c == '}':
            profundidad -= 1
            if encontrado_inicio_llave and profundidad == 0:
                fin = idx + 1
                break

    if fin == -1:
        print("ERROR " + nombre + ": no se pudo determinar el cierre de la funcion")
        continue

    funcion_actual = src[inicio:fin]
    if 'html2canvas' not in funcion_actual and 'doc.html(contenedor' not in funcion_actual:
        print("* " + nombre + ": la funcion no parece ser la version html2canvas, revisar manualmente")
        continue

    nueva_src = src[:inicio] + nueva_funcion_completa + src[fin:]
    open(ruta, 'w', encoding='utf-8').write(nueva_src)
    print("OK " + nombre + ": funcion reemplazada por dibujado manual con lineas punteadas")
    total += 1

print()
print("Total actualizado: " + str(total))
print()

ok_total = True
for nombre in ['pagos.html', 'historial.html']:
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
    print("Listo. El PDF ahora usa lineas punteadas de verdad y texto")
    print("completamente negro (0,0,0), dibujado directamente con jsPDF.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
