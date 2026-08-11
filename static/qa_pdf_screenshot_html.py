#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Genera el PDF tomando una captura (screenshot) del MISMO HTML que
usa Imprimir, e insertandola como imagen en el PDF. Mas confiable que
el metodo html() integrado de jsPDF que causo el crash anterior.
Uso: cd ~/inventario-qa/static && python3 qa_pdf_screenshot_html.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

# ================================================================
# 1. Agregar html2canvas como script separado (no solo el bundle de jsPDF)
# ================================================================
TAG_H2C = '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>\n'

for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    if 'html2canvas.min.js' not in src:
        marcador = '<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>'
        if marcador in src:
            src = src.replace(marcador, marcador + '\n' + TAG_H2C.strip(), 1)
            open(ruta, 'w', encoding='utf-8').write(src)
            print("OK " + nombre + ": script de html2canvas agregado")
        else:
            print("ERROR " + nombre + ": no se encontro el script de jsPDF")
    else:
        print("* " + nombre + ": html2canvas ya estaba agregado")

# ================================================================
# 2. Reemplazar generarPDFTicketVenta: screenshot + imagen en PDF
# ================================================================
def reemplazar_funcion(nombre, nombre_funcion_html):
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()

    inicio = src.find('async function generarPDFTicketVenta(v){')
    if inicio == -1:
        print("ERROR " + nombre + ": no se encontro generarPDFTicketVenta")
        return False
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
        return False

    nueva_funcion = '''async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;
  const contenedor = document.createElement('div');
  contenedor.style.position = 'absolute';
  contenedor.style.left = '-9999px';
  contenedor.style.top = '0';
  contenedor.style.width = '300px';
  contenedor.style.background = '#ffffff';
  contenedor.style.padding = '16px';
  contenedor.style.fontFamily = 'monospace';
  contenedor.style.fontSize = '13px';
  contenedor.style.color = '#000000';
  contenedor.innerHTML = ''' + nombre_funcion_html + '''(v);
  document.body.appendChild(contenedor);

  try{
    await new Promise(function(r){ setTimeout(r, 80); });
    const canvas = await html2canvas(contenedor, {scale:2, backgroundColor:'#ffffff', useCORS:true});
    const imgData = canvas.toDataURL('image/png');
    const pdfWidth = 320;
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    const doc = new jsPDFCtor({unit:'pt', format:[pdfWidth, pdfHeight], orientation:'portrait'});
    doc.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    return doc.output('blob');
  } finally {
    document.body.removeChild(contenedor);
  }
}'''

    src = src[:inicio] + nueva_funcion + src[fin:]
    open(ruta, 'w', encoding='utf-8').write(src)
    print("OK " + nombre + ": generarPDFTicketVenta ahora usa screenshot + imagen")
    return True

print()
reemplazar_funcion('pagos.html', 'generarTicketHTML')
reemplazar_funcion('historial.html', 'ticketHTML')

# ================================================================
# Verificar y reiniciar
# ================================================================
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
    print("Listo. Descargar y WhatsApp ahora usan una captura del mismo HTML")
    print("que usa Imprimir -- deberian verse identicos, y este metodo es")
    print("mas estable que el anterior (no debería trabarse).")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
