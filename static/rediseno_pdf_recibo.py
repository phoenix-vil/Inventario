#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rediseña el PDF del recibo de abono:
- Quita emojis y caracteres unicode que rompen las fuentes basicas de jsPDF.
- Agrega el logo real de la empresa (cargado desde /static/logo.png).
- Formato limpio tipo tabla (etiqueta izquierda, valor derecha) en vez de
  texto plano monoespaciado.
Uso: cd ~/inventario/static && python3 rediseno_pdf_recibo.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src

# ================================================================
# 1. Reemplazar generarPDFTicket + compartirComoPDF por las nuevas
#    versiones (logo, sin emojis, formato de tabla)
# ================================================================
patron_funciones = re.compile(
    r"function generarPDFTicket\(texto\)\{.*?\nasync function compartirComoPDF\(texto, nombreArchivo\)\{.*?\n\}\n",
    re.DOTALL
)

nuevas_funciones = '''function cargarImagenBase64(url){
  return new Promise(function(resolve, reject){
    fetch(url).then(function(r){ return r.blob(); }).then(function(blob){
      const reader = new FileReader();
      reader.onloadend = function(){ resolve(reader.result); };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    }).catch(reject);
  });
}

async function generarPDFRecibo(datos){
  const jsPDFCtor = window.jspdf.jsPDF;
  const doc = new jsPDFCtor({ unit: 'pt', format: [320, 440] });
  const centerX = 160;
  let y = 28;

  try{
    const logoData = await cargarImagenBase64('/static/logo.png');
    const logoW = 90;
    const logoH = 48;
    doc.addImage(logoData, 'PNG', centerX - logoW / 2, y, logoW, logoH);
    y += logoH + 14;
  }catch(e){
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.setTextColor(20);
    doc.text('ONLY ENTERPRISES', centerX, y + 10, {align:'center'});
    y += 30;
  }

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(20);
  doc.text('Recibo de abono', centerX, y, {align:'center'});
  y += 18;

  doc.setDrawColor(220);
  doc.line(24, y, 296, y);
  y += 20;

  function fila(label, valor, opts){
    opts = opts || {};
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(opts.size || 10);
    doc.setTextColor(120);
    doc.text(label, 24, y);
    doc.setFont('helvetica', opts.bold ? 'bold' : 'normal');
    if(opts.color){ doc.setTextColor(opts.color[0], opts.color[1], opts.color[2]); }
    else{ doc.setTextColor(20); }
    doc.text(String(valor), 296, y, {align:'right'});
    y += (opts.size || 10) + 8;
  }

  const fecha = new Date(datos.fecha).toLocaleString('es-MX');
  fila('Cliente', datos.cliente_nombre);
  fila('Fecha', fecha);
  if(datos.operador) fila('Atendió', datos.operador);
  if(datos.sucursal) fila('Sucursal', datos.sucursal);

  y += 4;
  doc.setDrawColor(220);
  doc.line(24, y, 296, y);
  y += 20;

  fila('Monto abonado', money(datos.monto), {size:12, bold:true, color:[59,109,17]});
  fila('Método', datos.metodo_pago);
  if(datos.nota) fila('Nota', datos.nota);

  y += 4;
  doc.line(24, y, 296, y);
  y += 20;

  const colorSaldo = datos.saldo_restante > 0 ? [163,45,45] : [59,109,17];
  fila('Saldo restante', money(datos.saldo_restante), {size:13, bold:true, color:colorSaldo});

  y += 20;
  doc.setFont('helvetica', 'italic');
  doc.setFontSize(10);
  doc.setTextColor(140);
  doc.text('Gracias por su pago', centerX, y, {align:'center'});

  return doc.output('blob');
}

async function compartirComoPDF(datos, nombreArchivo){
  const blob = await generarPDFRecibo(datos);
  const archivo = new File([blob], nombreArchivo, {type:'application/pdf'});

  if(navigator.canShare && navigator.canShare({files:[archivo]})){
    try{
      await navigator.share({files:[archivo]});
      return;
    }catch(e){
      if(e.name === 'AbortError') return;
    }
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nombreArchivo;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  alert('Tu navegador no permite compartir directo. Se descargó el PDF: adjúntalo manualmente en WhatsApp.');
}
'''

nueva_src, n1 = patron_funciones.subn(nuevas_funciones, src, count=1)
if n1 == 1:
    src = nueva_src
    print("1. Funciones de PDF rediseñadas (logo + tabla, sin emojis)")
else:
    print("1. ERROR: no se encontraron las funciones de PDF para reemplazar")
    print("   Revisar: grep -n 'generarPDFTicket\\|compartirComoPDF' clientes.html")

# ================================================================
# 2. compartirReciboWhatsApp(): pasar el objeto de datos, no el texto
# ================================================================
viejo = '''function compartirReciboWhatsApp(){
  if(!reciboActual) return;
  const txt = generarTextoRecibo(reciboActual);
  compartirComoPDF(txt, 'abono_' + reciboActual.id + '.pdf');
}'''

nuevo = '''function compartirReciboWhatsApp(){
  if(!reciboActual) return;
  compartirComoPDF(reciboActual, 'abono_' + reciboActual.id + '.pdf');
}'''

n2 = src.count(viejo)
if n2 == 1:
    src = src.replace(viejo, nuevo, 1)
    print("2. compartirReciboWhatsApp() ahora manda el objeto completo (para el logo/tabla)")
elif 'compartirComoPDF(reciboActual,' in src:
    print("2. * Ya estaba actualizado")
else:
    print("2. ERROR: no se encontro el bloque exacto (coincidencias: " + str(n2) + ")")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(CLIENTES, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. El PDF ahora tiene el logo real y un formato limpio, sin caracteres raros.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
