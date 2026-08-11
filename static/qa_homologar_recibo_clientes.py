#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Homologa el recibo de abono en clientes.html con el mismo diseno
que usa Punto de Venta: logo real, lineas punteadas SVG, formato de
tabla, y el mismo metodo de generacion de PDF (captura + imagen).
Uso: cd ~/inventario-qa/static && python3 qa_homologar_recibo_clientes.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario-qa/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Agregar html2canvas (CDN) si no existe
# ================================================================
if 'html2canvas.min.js' not in src:
    marcador = '<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>'
    tag_h2c = '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>'
    if marcador in src:
        src = src.replace(marcador, marcador + '\n' + tag_h2c, 1)
        cambios.append('script de html2canvas agregado')
    else:
        print("ERROR: no se encontro el script de jsPDF")
else:
    cambios.append('* html2canvas ya estaba')

# ================================================================
# 2. Agregar las clases CSS .tk-* (mismo estilo que Punto de Venta)
# ================================================================
if '.tk-line{' not in src:
    css_tickets = '''.tk-head,.tk-foot{text-align:center;margin:8px 0}
.tk-sub{font-size:12px;color:#000}
.tk-items{padding:8px 0;margin:8px 0}
.tk-line{display:flex;justify-content:space-between;margin-bottom:3px}
.tk-total{font-weight:700;font-size:16px;margin-top:8px;padding-top:8px}
.tk-desc{color:#a32d2d}
.tk-ahorro{color:#3b6d11;font-weight:bold}
'''
    marcador_css = '<link rel="stylesheet" href="/static/modern.css">'
    if marcador_css in src:
        src = src.replace(marcador_css, '<style>\n' + css_tickets + '</style>\n' + marcador_css, 1)
        cambios.append('clases CSS de ticket agregadas')
    else:
        print("ERROR: no se encontro el link de modern.css para insertar el CSS")
else:
    cambios.append('* CSS de ticket ya existia')

# ================================================================
# 3. Agregar generarReciboHTML(v)
# ================================================================
if 'function generarReciboHTML' not in src:
    funcion_html = '''function generarReciboHTML(v){
  const fecha = new Date(v.fecha).toLocaleString('es-MX');
  const logoSrc = _logoCacheDataUrl || '/static/logo.png';
  const RAYA = '<svg width="100%" height="3" style="display:block;margin:6px 0"><line x1="0" y1="1.5" x2="100%" y2="1.5" stroke="#000" stroke-width="1" stroke-dasharray="4,3"/></svg>';
  let html = `<div class="tk-head">
    <img src="${logoSrc}" alt="Only Enterprises" style="height:44px;width:auto;margin-bottom:6px">
    <div class="tk-sub">Recibo de abono</div>
  </div>${RAYA}`;
  html += `<div class="tk-line"><span>Cliente</span><span>${esc(v.cliente_nombre)}</span></div>`;
  html += `<div class="tk-line"><span>Fecha</span><span>${fecha}</span></div>`;
  if(v.operador) html += `<div class="tk-line"><span>Atendió</span><span>${esc(v.operador)}</span></div>`;
  if(v.sucursal) html += `<div class="tk-line"><span>Sucursal</span><span>${esc(v.sucursal)}</span></div>`;
  html += RAYA;
  html += `<div class="tk-line"><span>Monto abonado</span><span>${money(v.monto)}</span></div>`;
  html += `<div class="tk-line"><span>Método</span><span>${esc(v.metodo_pago)}</span></div>`;
  if(v.nota) html += `<div class="tk-line"><span>Nota</span><span>${esc(v.nota)}</span></div>`;
  html += RAYA;
  html += `<div class="tk-line tk-total"><span>Saldo restante</span><span>${money(v.saldo_restante)}</span></div>`;
  html += '<div class="tk-foot">¡Gracias por su pago!</div>';
  return html;
}

'''
    marcador_func = 'async function generarPDFRecibo(datos){'
    if marcador_func in src:
        src = src.replace(marcador_func, funcion_html + marcador_func, 1)
        cambios.append('generarReciboHTML() agregada')
    else:
        print("ERROR: no se encontro 'async function generarPDFRecibo(datos){'")
else:
    cambios.append('* generarReciboHTML ya existia')

# ================================================================
# 4. Reemplazar generarPDFRecibo (captura + imagen, en vez de
#    dibujado manual con la funcion fila())
# ================================================================
inicio = src.find('async function generarPDFRecibo(datos){')
if inicio != -1:
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
    if fin != -1:
        funcion_actual = src[inicio:fin]
        if 'html2canvas(contenedor' not in funcion_actual:
            nueva_funcion = '''async function generarPDFRecibo(datos){
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
  contenedor.innerHTML = generarReciboHTML(datos);
  contenedor.querySelectorAll('.tk-sub, .tk-foot, .tk-line, .tk-total').forEach(function(el){ el.style.color = '#000000'; });
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
            cambios.append('generarPDFRecibo() reemplazada (captura + imagen)')
        else:
            cambios.append('* generarPDFRecibo ya usaba el metodo de captura')
    else:
        print("ERROR: no se pudo determinar el cierre de generarPDFRecibo")
else:
    print("ERROR: no se encontro generarPDFRecibo (post-insercion)")

# ================================================================
# 5. Actualizar el estilo del contenedor recibo-contenido (quitar
#    monospace/pre-line forzado, dejar que el HTML se vea normal)
# ================================================================
viejo_div = '<div id="recibo-contenido" style="background:var(--bg);border-radius:10px;padding:1.25rem;margin-bottom:1rem;font-family:ui-monospace,monospace;font-size:13px;white-space:pre-line"></div>'
nuevo_div = '<div id="recibo-contenido" style="background:#fff;border-radius:10px;padding:1.25rem;margin-bottom:1rem;color:#000"></div>'
if viejo_div in src:
    src = src.replace(viejo_div, nuevo_div, 1)
    cambios.append('contenedor de vista previa actualizado')
elif 'id="recibo-contenido" style="background:#fff' in src:
    cambios.append('* contenedor ya estaba actualizado')

# ================================================================
# 6. mostrarRecibo(): usar el HTML en vez de texto plano
# ================================================================
viejo_mostrar = '''function mostrarRecibo(data){
  reciboActual = data;
  document.getElementById('recibo-contenido').textContent = generarTextoRecibo(data);
  document.getElementById('modal-recibo').classList.add('open');
}'''
nuevo_mostrar = '''function mostrarRecibo(data){
  reciboActual = data;
  document.getElementById('recibo-contenido').innerHTML = generarReciboHTML(data);
  document.getElementById('modal-recibo').classList.add('open');
}'''
if viejo_mostrar in src:
    src = src.replace(viejo_mostrar, nuevo_mostrar, 1)
    cambios.append('mostrarRecibo() muestra el HTML con el diseno nuevo')
elif "recibo-contenido').innerHTML = generarReciboHTML" in src:
    cambios.append('* mostrarRecibo ya usaba el HTML')

# ================================================================
# 7. descargarRecibo(): descargar el PDF (no .txt)
# ================================================================
viejo_descargar = '''function descargarRecibo(){
  if(!reciboActual) return;
  const txt = generarTextoRecibo(reciboActual);
  const blob = new Blob([txt], {type:'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'abono_' + reciboActual.id + '.txt';
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}'''
nuevo_descargar = '''async function descargarRecibo(){
  if(!reciboActual) return;
  const blob = await generarPDFRecibo(reciboActual);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'abono_' + reciboActual.id + '.pdf';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 3000);
}'''
if viejo_descargar in src:
    src = src.replace(viejo_descargar, nuevo_descargar, 1)
    cambios.append('descargarRecibo() ahora baja PDF')
elif 'async function descargarRecibo(){\n  if(!reciboActual) return;\n  const blob = await generarPDFRecibo' in src:
    cambios.append('* descargarRecibo ya bajaba PDF')

# ================================================================
# 8. imprimirRecibo(): usar el HTML con el diseno (no texto con <br>)
# ================================================================
viejo_imprimir = '''function imprimirRecibo(){
  if(!reciboActual) return;
  const win = window.open('', '_blank');
  const txtHtml = generarTextoRecibo(reciboActual).replace(/\\n/g,'<br>');
  win.document.write('<html><head><title>Recibo de abono</title><style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto}</style></head><body>' + txtHtml + '</body></html>');
  win.document.close();
  setTimeout(function(){win.print();}, 300);
}'''
nuevo_imprimir = '''function imprimirRecibo(){
  if(!reciboActual) return;
  const win = window.open('', '_blank');
  const estilos = '<style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto;color:#000}'
    + '.tk-head,.tk-foot{text-align:center;margin:8px 0}.tk-sub{font-size:12px;color:#000}'
    + '.tk-line{display:flex;justify-content:space-between;margin-bottom:3px}'
    + '.tk-total{font-weight:700;font-size:16px;margin-top:8px;padding-top:8px}</style>';
  win.document.write('<html><head><title>Recibo de abono</title>' + estilos + '</head><body>' + generarReciboHTML(reciboActual) + '</body></html>');
  win.document.close();
  setTimeout(function(){win.print();}, 300);
}'''
if viejo_imprimir in src:
    src = src.replace(viejo_imprimir, nuevo_imprimir, 1)
    cambios.append('imprimirRecibo() usa el HTML con el diseno')
elif "generarReciboHTML(reciboActual) + '</body>" in src:
    cambios.append('* imprimirRecibo ya usaba el HTML')

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(CLIENTES, 'w', encoding='utf-8').write(src)
    print()
    for c in cambios:
        print("OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El recibo de abono ahora usa el mismo diseno (logo, lineas")
    print("punteadas, formato de tabla) en pantalla, Descargar, Imprimir y WhatsApp.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
