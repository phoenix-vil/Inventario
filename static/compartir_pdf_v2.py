#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version 2, basada en el contenido REAL confirmado del archivo:
agrega las funciones de generar/compartir PDF, y reemplaza
compartirReciboWhatsApp() para que use PDF en vez de wa.me con texto.
Uso: cd ~/inventario/static && python3 compartir_pdf_v2.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar las funciones de PDF (si no existen ya)
# ================================================================
if 'function generarPDFTicket' not in src:
    funciones = '''function generarPDFTicket(texto){
  const jsPDFCtor = window.jspdf.jsPDF;
  const lineas = texto.split('\\n');
  const fontSize = 10;
  const lineHeight = fontSize * 1.5;
  const margin = 20;
  const alturaTotal = Math.max(200, lineas.length * lineHeight + margin * 2);

  const doc = new jsPDFCtor({ unit: 'pt', format: [300, alturaTotal] });
  doc.setFont('courier', 'normal');
  doc.setFontSize(fontSize);

  lineas.forEach(function(linea, i){
    doc.text(linea, margin, margin + (i + 1) * lineHeight - lineHeight * 0.3);
  });

  return doc.output('blob');
}

async function compartirComoPDF(texto, nombreArchivo){
  const blob = generarPDFTicket(texto);
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
    marcador = 'let reciboActual = null;'
    if marcador in src:
        src = src.replace(marcador, funciones + marcador, 1)
        print("1. Funciones generarPDFTicket/compartirComoPDF agregadas")
    else:
        print("1. ERROR: no se encontro 'let reciboActual = null;'")
else:
    print("1. * Las funciones de PDF ya existian")

# ================================================================
# 2. Reemplazar compartirReciboWhatsApp() (version real confirmada)
# ================================================================
viejo = '''function compartirReciboWhatsApp(){
  if(!reciboActual) return;
  const txt = generarTextoRecibo(reciboActual);
  window.open('https://wa.me/?text=' + encodeURIComponent(txt), '_blank');
}'''

nuevo = '''function compartirReciboWhatsApp(){
  if(!reciboActual) return;
  const txt = generarTextoRecibo(reciboActual);
  compartirComoPDF(txt, 'abono_' + reciboActual.id + '.pdf');
}'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("2. compartirReciboWhatsApp() ahora comparte un PDF real")
elif 'compartirComoPDF(txt' in src:
    print("2. * Ya estaba actualizado")
else:
    print("2. ERROR: no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

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
    print("Listo. Prueba de nuevo: registrar un abono y compartir por WhatsApp")
    print("deberia abrir el panel nativo de compartir con un PDF adjunto.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
