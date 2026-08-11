#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cambia el ticket compartido de imagen PNG a PDF, usando la libreria
jsPDF (cargada desde CDN). Reemplaza generarImagenTicket/compartirComoImagen
por generarPDFTicket/compartirComoPDF.
Uso: cd ~/inventario/static && python3 compartir_pdf_ticket.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar el script de jsPDF (CDN) antes de auth.js
# ================================================================
if 'jspdf' not in src.lower():
    tag_jspdf = '<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>\n'
    marcador = '<script src="/static/auth.js"></script>'
    if marcador in src:
        src = src.replace(marcador, tag_jspdf + marcador, 1)
        print("1. Script de jsPDF (CDN) agregado")
    else:
        print("1. ERROR: no se encontro '<script src=\"/static/auth.js\"></script>'")
else:
    print("1. * jsPDF ya estaba agregado")

# ================================================================
# 2. Reemplazar las funciones de imagen por las de PDF
#    (contempla que el paso anterior haya quedado en PNG o siga en wa.me)
# ================================================================
patron_funciones = re.compile(
    r"function generarImagenTicket\(texto\)\{.*?\nasync function compartirComoImagen\(texto, nombreArchivo\)\{.*?\n\}\n",
    re.DOTALL
)

nuevas_funciones = '''function generarPDFTicket(texto){
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

nueva_src, n1 = patron_funciones.subn(nuevas_funciones, src, count=1)
if n1 == 1:
    src = nueva_src
    print("2. Funciones reemplazadas: ahora generan PDF en vez de PNG")
elif 'function generarPDFTicket' in src:
    print("2. * Ya estaba en PDF")
else:
    print("2. ERROR: no se encontraron las funciones de imagen para reemplazar")
    print("   Revisar manualmente: grep -n 'generarImagenTicket\\|compartirComoImagen' clientes.html")

# ================================================================
# 3. Actualizar compartirReciboWhatsApp() para usar PDF y extension .pdf
# ================================================================
viejo_llamada = "compartirComoImagen(txt, 'abono_' + reciboActual.id + '.png');"
nueva_llamada = "compartirComoPDF(txt, 'abono_' + reciboActual.id + '.pdf');"

n2 = src.count(viejo_llamada)
if n2 == 1:
    src = src.replace(viejo_llamada, nueva_llamada, 1)
    print("3. compartirReciboWhatsApp() ahora pide un PDF (.pdf)")
elif "compartirComoPDF(txt, 'abono_'" in src:
    print("3. * Ya estaba actualizado")
else:
    print("3. ERROR: no se encontro la llamada exacta a compartirComoImagen")

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
    print("Listo. El boton de WhatsApp del recibo ahora comparte un PDF real.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
