#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Solucion definitiva: las lineas punteadas del ticket pasan de CSS
(border-dashed, que html2canvas no captura bien) a SVG explicito dentro
del HTML. Se quitan los bordes CSS duplicados, y el PDF se genera
convirtiendo el MISMO HTML que usa la pantalla/impresion.
Uso: cd ~/inventario-qa/static && python3 qa_svg_lineas_definitivo.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

RAYA_SVG = '<svg width="100%" height="3" style="display:block;margin:6px 0"><line x1="0" y1="1.5" x2="100%" y2="1.5" stroke="#000" stroke-width="1" stroke-dasharray="4,3"/></svg>'

def procesar_archivo(nombre, nombre_funcion_html):
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    cambios = []

    # ---- 1. Quitar bordes CSS duplicados (CSS principal) ----
    viejo_css_items = '.tk-items{border-top:1px dashed var(--border);border-bottom:1px dashed var(--border);padding:8px 0;margin:8px 0}'
    nuevo_css_items = '.tk-items{padding:8px 0;margin:8px 0}'
    if viejo_css_items in src:
        src = src.replace(viejo_css_items, nuevo_css_items, 1)
        cambios.append('CSS principal .tk-items sin borde')

    viejo_css_total = '.tk-total{font-weight:700;font-size:16px;border-top:1px dashed var(--border);margin-top:8px;padding-top:8px}'
    nuevo_css_total = '.tk-total{font-weight:700;font-size:16px;margin-top:8px;padding-top:8px}'
    if viejo_css_total in src:
        src = src.replace(viejo_css_total, nuevo_css_total, 1)
        cambios.append('CSS principal .tk-total sin borde')

    # ---- 2. Quitar bordes CSS duplicados (bloque de impresion) ----
    viejo_print_items = '.tk-negocio{font-size:18px;font-weight:bold}.tk-items{border-top:1px dashed #000;border-bottom:1px dashed #000;padding:6px 0;margin:6px 0}'
    nuevo_print_items = '.tk-negocio{font-size:18px;font-weight:bold}.tk-items{padding:6px 0;margin:6px 0}'
    if viejo_print_items in src:
        src = src.replace(viejo_print_items, nuevo_print_items, 1)
        cambios.append('CSS de impresion .tk-items sin borde')

    viejo_print_total = '.tk-total{font-weight:bold;font-size:15px;border-top:1px dashed #000;margin-top:6px;padding-top:6px}'
    nuevo_print_total = '.tk-total{font-weight:bold;font-size:15px;margin-top:6px;padding-top:6px}'
    if viejo_print_total in src:
        src = src.replace(viejo_print_total, nuevo_print_total, 1)
        cambios.append('CSS de impresion .tk-total sin borde')

    # ---- 3. Agregar las lineas SVG en generarTicketHTML/ticketHTML ----
    viejo_funcion = '''  </div><div class="tk-items">`;
  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(it.importe)}</span></div>`;
  });
  html+='</div>';'''

    nuevo_funcion = '''  </div>${RAYA}<div class="tk-items">`;
  (v.detalle||[]).forEach(it=>{
    const cant=Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    html+=`<div class="tk-line"><span>${cant} ${esc(it.nombre)}</span><span>${money(it.importe)}</span></div>`;
  });
  html+='</div>'+RAYA;'''

    if viejo_funcion in src:
        src = src.replace(viejo_funcion, nuevo_funcion, 1)
        cambios.append('raya SVG agregada antes/despues de items')

    viejo_total_line = '''  html+=`<div class="tk-line tk-total"><span>TOTAL</span><span>${money(v.total)}</span></div>`;
  if(v.metodo_pago==='credito'){'''
    nuevo_total_line = '''  html+=`<div class="tk-line tk-total"><span>TOTAL</span><span>${money(v.total)}</span></div>`+RAYA;
  if(v.metodo_pago==='credito'){'''
    if viejo_total_line in src:
        src = src.replace(viejo_total_line, nuevo_total_line, 1)
        cambios.append('raya SVG agregada despues de TOTAL')

    # Definir la constante RAYA dentro de la funcion (justo despues de logoSrc)
    viejo_logosrc = "const logoSrc=_logoCacheDataUrl||'/static/logo.png';"
    nuevo_logosrc = "const logoSrc=_logoCacheDataUrl||'/static/logo.png';\n  const RAYA='" + RAYA_SVG.replace("'", "\\'") + "';"
    if viejo_logosrc in src and 'const RAYA=' not in src:
        src = src.replace(viejo_logosrc, nuevo_logosrc, 1)
        cambios.append('constante RAYA definida')

    if cambios:
        open(ruta, 'w', encoding='utf-8').write(src)
        for c in cambios:
            print("OK " + nombre + ": " + c)
    else:
        print("* " + nombre + ": no se encontraron patrones para la parte HTML/CSS (revisar)")

    return src

src_pagos = procesar_archivo('pagos.html', 'generarTicketHTML')
print()
src_hist = procesar_archivo('historial.html', 'ticketHTML')
print()

# ================================================================
# 4. Reemplazar generarPDFTicketVenta para usar html2canvas + el HTML real
# ================================================================
def reemplazar_pdf(nombre, nombre_funcion_html):
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()

    inicio = src.find('async function generarPDFTicketVenta(v){')
    if inicio == -1:
        print("ERROR " + nombre + ": no se encontro generarPDFTicketVenta")
        return
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
        return

    nueva_funcion = '''async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;
  const contenedor = document.createElement('div');
  contenedor.setAttribute('style', 'position:fixed;left:0;top:0;width:300px;background:#ffffff;padding:16px;font-family:monospace;font-size:13px;color:#000000;z-index:-1000;opacity:0.01');
  contenedor.innerHTML = ''' + nombre_funcion_html + '''(v);
  document.body.appendChild(contenedor);
  await new Promise(function(r){ setTimeout(r, 50); });

  return new Promise(function(resolve){
    const doc = new jsPDFCtor({unit:'pt', format:[320, 700], orientation:'portrait'});
    doc.html(contenedor, {
      x: 10, y: 10,
      width: 300,
      windowWidth: 300,
      html2canvas: {scale: 2, backgroundColor: '#ffffff'},
      callback: function(docFinal){
        document.body.removeChild(contenedor);
        resolve(docFinal.output('blob'));
      }
    });
  });
}'''

    src = src[:inicio] + nueva_funcion + src[fin:]
    open(ruta, 'w', encoding='utf-8').write(src)
    print("OK " + nombre + ": generarPDFTicketVenta reemplazada (usa " + nombre_funcion_html + " + html2canvas)")

reemplazar_pdf('pagos.html', 'generarTicketHTML')
reemplazar_pdf('historial.html', 'ticketHTML')

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
    print("Listo. Descargar/WhatsApp ahora convierten el HTML REAL (con lineas")
    print("SVG) a PDF -- deberia verse identico a Imprimir esta vez.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
