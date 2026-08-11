#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rediseña el ticket de venta compartido por WhatsApp en historial.html:
logo real, formato de tabla limpio, PDF compartible (en vez de texto).
Uso: cd ~/inventario/static && python3 pdf_ticket_historial.py
"""
import os, re

HIST = os.path.expanduser('~/inventario/static/historial.html')
src = open(HIST, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Agregar el script de jsPDF (CDN) si no existe
# ================================================================
if 'jspdf' not in src.lower():
    tag_jspdf = '<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>\n'
    marcador = '<script src="/static/auth.js"></script>'
    if marcador in src:
        src = src.replace(marcador, tag_jspdf + marcador, 1)
        cambios.append('script de jsPDF agregado')
    else:
        print("ERROR: no se encontro el script de auth.js")
else:
    print("* jsPDF ya estaba agregado")

# ================================================================
# 2. Agregar las funciones de PDF (mismas que en pagos.html)
# ================================================================
if 'function generarPDFTicketVenta' not in src:
    funciones = '''function cargarImagenBase64(url){
  return new Promise(function(resolve, reject){
    fetch(url).then(function(r){ return r.blob(); }).then(function(blob){
      const reader = new FileReader();
      reader.onloadend = function(){ resolve(reader.result); };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    }).catch(reject);
  });
}

async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;
  const numItems = (v.detalle||[]).length;
  let alturaEstimada = 260 + numItems * 15;
  if(v.descuento_extra_pct>0) alturaEstimada += 36;
  const ahorroTk0 = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk0>0.005) alturaEstimada += 18;

  const doc = new jsPDFCtor({ unit:'pt', format:[320, alturaEstimada] });
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

  doc.setFont('helvetica','normal'); doc.setFontSize(9); doc.setTextColor(120);
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
}

async function compartirComoPDFVenta(v, nombreArchivo){
  const blob = await generarPDFTicketVenta(v);
  const archivo = new File([blob], nombreArchivo, {type:'application/pdf'});
  if(navigator.canShare && navigator.canShare({files:[archivo]})){
    try{ await navigator.share({files:[archivo]}); return; }
    catch(e){ if(e.name==='AbortError') return; }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nombreArchivo;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  alert('Tu navegador no permite compartir directo. Se descargó el PDF: adjúntalo manualmente en WhatsApp.');
}

'''
    marcador2 = 'function ticketHTML(v){'
    if marcador2 in src:
        src = src.replace(marcador2, funciones + marcador2, 1)
        cambios.append('funciones de PDF agregadas')
    else:
        print("ERROR: no se encontro 'function ticketHTML(v){'")
else:
    print("* Las funciones de PDF ya existian")

# ================================================================
# 3. Reemplazar compartirWhatsApp() para usar PDF
# ================================================================
viejo = '''function compartirWhatsApp(){
  const txt=ticketTextoPlano(ventaDetalle);
  if(!txt)return;
  window.open('https://wa.me/?text='+encodeURIComponent(txt),'_blank');
}'''

nuevo = '''function compartirWhatsApp(){
  if(!ventaDetalle)return;
  compartirComoPDFVenta(ventaDetalle, 'ticket_'+ventaDetalle.id+'.pdf');
}'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    cambios.append('compartirWhatsApp() ahora comparte un PDF')
elif 'compartirComoPDFVenta(ventaDetalle' in src:
    print("* compartirWhatsApp ya estaba actualizado")
else:
    print("ERROR: no se encontro el bloque exacto de compartirWhatsApp (coincidencias: " + str(n) + ")")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(HIST, 'w', encoding='utf-8').write(src)
    print()
    for c in cambios:
        print("OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. El ticket de venta en Historial ahora comparte un PDF con logo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
