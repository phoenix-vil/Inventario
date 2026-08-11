#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Reemplaza descargarTicket()/descargarTicketDetalle() (que bajaban
un .txt plano) para que descarguen el mismo PDF con logo que ya usa
"Compartir por WhatsApp".
Uso: cd ~/inventario-qa/static && python3 qa_fix_descargar_pdf.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

# ================================================================
# PAGOS.HTML
# ================================================================
pagos_path = os.path.join(STATIC, 'pagos.html')
src = open(pagos_path, encoding='utf-8').read()
original = src

viejo_pagos = '''function descargarTicket(){
  if(!ticketActual)return;
  const v=ticketActual;
  const fecha=new Date(v.fecha).toLocaleString('es-MX');
  let txt=`        MI NEGOCIO\\n   Ticket de venta #${v.id}\\n   ${fecha}\\n`;
  txt+='--------------------------------\\n';
  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    txt+=`${cant} ${it.nombre}\\n`.padEnd(24)+`${money(it.importe)}\\n`;
  });
  txt+='--------------------------------\\n';
  if(v.descuento_extra_pct>0){
    txt+=`Subtotal: ${money(v.subtotal)}\\n`;
    txt+=`Descuento ${v.descuento_extra_pct}%: -${money(v.subtotal*v.descuento_extra_pct/100)}\\n`;
  }
  const ahorroDl=v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroDl>0.005){
    txt+=`Ahorraste: ${money(ahorroDl)}\\n`;
  }
  txt+=`TOTAL: ${money(v.total)}\\n`;
  if(v.pago_con!=null){txt+=`Pagó con: ${money(v.pago_con)}\\nCambio: ${money(v.cambio||0)}\\n`;}
  txt+='\\n   ¡Gracias por su compra!\\n';
  const blob=new Blob([txt],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download=`ticket_${v.id}.txt`;
  document.body.appendChild(a);a.click();a.remove();
  URL.revokeObjectURL(url);
}'''

nuevo_pagos = '''async function descargarTicket(){
  if(!ticketActual)return;
  const blob = await generarPDFTicketVenta(ticketActual);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'ticket_' + ticketActual.id + '.pdf';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 3000);
}'''

n1 = src.count(viejo_pagos)
if n1 == 1:
    src = src.replace(viejo_pagos, nuevo_pagos, 1)
    print("1. pagos.html: descargarTicket() ahora genera PDF con logo")
elif 'generarPDFTicketVenta(ticketActual)' in src:
    print("1. * pagos.html: ya estaba actualizado")
else:
    print("1. ERROR: no se encontro el bloque exacto en pagos.html")

if src != original:
    open(pagos_path, 'w', encoding='utf-8').write(src)

scripts_pagos = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok_pagos = all(s.count('{') == s.count('}') for s in scripts_pagos)
print("   Balance de llaves en pagos.html:", "OK" if ok_pagos else "DESBALANCEADO")

# ================================================================
# HISTORIAL.HTML
# ================================================================
hist_path = os.path.join(STATIC, 'historial.html')
src2 = open(hist_path, encoding='utf-8').read()
original2 = src2

viejo_hist = '''function descargarTicketDetalle(){
  if(!ventaDetalle)return;
  const v=ventaDetalle;
  const fecha=new Date(v.fecha).toLocaleString('es-MX');
  let txt=`        MI NEGOCIO\\n   Ticket de venta #${v.id}\\n   ${fecha}\\n--------------------------------\\n`;
  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    txt+=`${cant} ${it.nombre} - ${money(it.importe)}\\n`;
  });
  txt+='--------------------------------\\n';
  if(v.descuento_extra_pct>0){
    txt+=`Subtotal: ${money(v.subtotal)}\\nDescuento ${v.descuento_extra_pct}%: -${money(v.subtotal*v.descuento_extra_pct/100)}\\n`;
  }
  const ahorroDl=v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroDl>0.005){
    txt+=`Ahorraste: ${money(ahorroDl)}\\n`;
  }
  txt+=`TOTAL: ${money(v.total)}\\n`;
  if(v.pago_con!=null){txt+=`Pagó con: ${money(v.pago_con)}\\nCambio: ${money(v.cambio||0)}\\n`;}
  txt+='\\n   ¡Gracias por su compra!\\n';
  bajarArchivo(txt,`ticket_${v.id}.txt`,'text/plain');
}'''

nuevo_hist = '''async function descargarTicketDetalle(){
  if(!ventaDetalle)return;
  const blob = await generarPDFTicketVenta(ventaDetalle);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'ticket_' + ventaDetalle.id + '.pdf';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 3000);
}'''

n2 = src2.count(viejo_hist)
if n2 == 1:
    src2 = src2.replace(viejo_hist, nuevo_hist, 1)
    print("2. historial.html: descargarTicketDetalle() ahora genera PDF con logo")
elif 'generarPDFTicketVenta(ventaDetalle)' in src2:
    print("2. * historial.html: ya estaba actualizado")
else:
    print("2. ERROR: no se encontro el bloque exacto en historial.html")

if src2 != original2:
    open(hist_path, 'w', encoding='utf-8').write(src2)

scripts_hist = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src2, re.DOTALL)
ok_hist = all(s.count('{') == s.count('}') for s in scripts_hist)
print("   Balance de llaves en historial.html:", "OK" if ok_hist else "DESBALANCEADO")

print()
print("=" * 55)
if ok_pagos and ok_hist:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El boton 'Descargar' ahora baja un PDF con el logo,")
    print("igual de bien formateado que el que se comparte por WhatsApp.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
