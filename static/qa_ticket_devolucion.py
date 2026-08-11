#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega el ticket de comprobante al confirmar una devolucion o
cancelacion, con el mismo formato que los demas (logo, lineas punteadas)
y los mismos botones: WhatsApp / Descargar / Imprimir.
Uso: cd ~/inventario-qa/static && python3 qa_ticket_devolucion.py
"""
import os, re

DEV = os.path.expanduser('~/inventario-qa/static/devoluciones.html')
src = open(DEV, encoding='utf-8').read()
res = []

# ============================================================
# 1. Librerias jsPDF + html2canvas
# ============================================================
if 'jspdf.umd.min.js' not in src:
    libs = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>\n'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>\n')
    if '<script src="/static/auth.js"></script>' in src:
        src = src.replace('<script src="/static/auth.js"></script>', libs + '<script src="/static/auth.js"></script>', 1)
        res.append("OK: librerias jsPDF y html2canvas agregadas")
    else:
        res.append("ERROR: no se encontro el script de auth.js")
else:
    res.append("* las librerias ya estaban")

# ============================================================
# 2. CSS del ticket + modal
# ============================================================
if '.tk-line{' not in src:
    css = '''<style>
.tk-head,.tk-foot{text-align:center;margin:8px 0}
.tk-sub{font-size:12px;color:var(--text);text-align:center}
.tk-items{padding:8px 0;margin:8px 0}
.tk-line{display:flex;justify-content:space-between;margin-bottom:3px}
.tk-total{font-weight:700;font-size:16px;margin-top:8px;padding-top:8px}
.tk-desc{color:var(--red)}
#tk-contenido{background:#fff;border-radius:10px;padding:1.25rem;margin-bottom:1rem;color:#000}
.tk-botones{display:flex;flex-direction:column;gap:8px}
.tk-botones .fila{display:flex;gap:8px}
.tk-btn-wa{width:100%;height:46px;border:none;border-radius:10px;background:#25D366;color:#fff;font-weight:700;font-size:15px;cursor:pointer}
.tk-btn-sec{flex:1;height:44px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-weight:600;font-size:14px;cursor:pointer;box-sizing:border-box}
</style>
'''
    i = src.find('</head>')
    if i != -1:
        src = src[:i] + css + src[i:]
        res.append("OK: estilos del ticket agregados")
    else:
        res.append("ERROR: no se encontro </head>")
else:
    res.append("* los estilos del ticket ya estaban")

# ============================================================
# 3. Modal del ticket
# ============================================================
if 'id="tk-modal"' not in src:
    modal = '''
<!-- Modal del ticket de devolucion -->
<div class="overlay" id="tk-modal">
  <div class="modal">
    <h2 id="tk-titulo">Comprobante</h2>
    <div id="tk-contenido"></div>
    <div class="tk-botones">
      <button class="tk-btn-wa" onclick="tkCompartirWhatsApp()">Compartir por WhatsApp</button>
      <div class="fila">
        <button class="tk-btn-sec" onclick="tkDescargar()">Descargar</button>
        <button class="tk-btn-sec" onclick="tkImprimir()">Imprimir</button>
      </div>
      <div class="fila">
        <button class="tk-btn-sec" onclick="tkCerrar()">Cerrar</button>
      </div>
    </div>
  </div>
</div>
'''
    m = re.search(r'</script>\s*</body>', src)
    i = src.rfind('</body>')
    if i != -1:
        src = src[:i] + modal + src[i:]
        res.append("OK: modal del ticket agregado")
    else:
        res.append("ERROR: no se encontro </body>")
else:
    res.append("* el modal ya existia")

# ============================================================
# 4. Funciones del ticket
# ============================================================
if 'function tkGenerarHTML' not in src:
    js = '''
// ─── Ticket de devolucion / cancelacion ─────────────────────────────────
let _logoCacheDataUrl = null;
let tkActual = null;

function cargarImagenBase64(url){
  if(_logoCacheDataUrl) return Promise.resolve(_logoCacheDataUrl);
  return new Promise(function(resolve, reject){
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function(){
      const c = document.createElement('canvas');
      const esc = 240 / img.width;
      c.width = 240; c.height = Math.round(img.height * esc);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      _logoCacheDataUrl = c.toDataURL('image/png');
      resolve(_logoCacheDataUrl);
    };
    img.onerror = reject;
    img.src = url;
  });
}
cargarImagenBase64('/static/logo.png').catch(function(){});

function fmtPct(p){const n=Math.round((Number(p)||0)*100)/100;return (n%1===0)?String(n):n.toFixed(2).replace(/0$/,'');}

function tkGenerarHTML(v){
  const fecha = new Date(v.fecha).toLocaleString('es-MX').replace(',', '');
  const logoSrc = _logoCacheDataUrl || '/static/logo.png';
  const RAYA = '<svg width="100%" height="3" style="display:block;margin:6px 0"><line x1="0" y1="1.5" x2="100%" y2="1.5" stroke="#000" stroke-width="1" stroke-dasharray="4,3"/></svg>';
  const nombresMet = {efectivo:'EFECTIVO', tarjeta:'TARJETA', credito:'A CRÉDITO', transferencia:'TRANSFERENCIA'};

  let html = '<div class="tk-head">'
    + '<img src="' + logoSrc + '" alt="Only Enterprises" style="height:44px;width:auto;margin-bottom:6px">'
    + '<div class="tk-sub">COMPROBANTE DE DEVOLUCIÓN</div>'
    + (v.sucursal ? '<div class="tk-sub">Sucursal ' + esc(v.sucursal) + '</div>' : '')
    + '<div class="tk-sub">Devolución #' + v.id + '</div>'
    + (v.venta_origen_id ? '<div class="tk-sub">Ticket original #' + v.venta_origen_id + '</div>' : '')
    + '<div class="tk-sub">' + fecha + '</div>'
    + (v.operador ? '<div class="tk-sub">Operador: ' + esc(v.operador) + '</div>' : '')
    + '</div>' + RAYA;

  (v.detalle || []).forEach(function(it){
    const cant = Math.abs(it.cantidad);
    const c = Number.isInteger(cant) ? cant + 'x' : cant.toFixed(3) + 'kg';
    html += '<div class="tk-line"><span>' + c + ' ' + esc(it.nombre) + '</span><span>' + money(it.importe) + '</span></div>';
  });
  html += RAYA;

  if(v.descuento_extra_pct > 0){
    html += '<div class="tk-line"><span>Subtotal</span><span>' + money(v.subtotal) + '</span></div>';
    html += '<div class="tk-line tk-desc"><span>Descuento ' + fmtPct(v.descuento_extra_pct) + '%</span><span>'
      + money(-(v.subtotal * v.descuento_extra_pct / 100)) + '</span></div>';
  }
  html += '<div class="tk-line tk-total"><span>TOTAL DEVUELTO</span><span>' + money(v.total) + '</span></div>';
  html += RAYA;
  html += '<div class="tk-line"><span>Reembolso</span><span>' + (nombresMet[v.metodo_pago] || v.metodo_pago) + '</span></div>';
  if(v.autorizado_por){
    html += '<div class="tk-line"><span>Motivo</span><span>' + esc(v.autorizado_por) + '</span></div>';
  }
  html += '<div class="tk-foot">Conserve este comprobante</div>';
  return html;
}

async function tkMostrar(idDevolucion, esCancelacion){
  try{
    const r = await authFetch('/api/ventas/' + idDevolucion);
    if(!r.ok) return;
    tkActual = await r.json();
    document.getElementById('tk-titulo').textContent = esCancelacion ? 'Comprobante de cancelación' : 'Comprobante de devolución';
    document.getElementById('tk-contenido').innerHTML = tkGenerarHTML(tkActual);
    document.getElementById('tk-modal').classList.add('open');
  }catch(e){}
}

function tkCerrar(){ document.getElementById('tk-modal').classList.remove('open'); }

async function tkGenerarPDF(){
  const jsPDFCtor = window.jspdf.jsPDF;
  const cont = document.createElement('div');
  cont.style.position = 'absolute';
  cont.style.left = '-9999px';
  cont.style.top = '0';
  cont.style.width = '300px';
  cont.style.background = '#ffffff';
  cont.style.padding = '16px 24px';
  cont.style.boxSizing = 'border-box';
  cont.style.fontFamily = 'monospace';
  cont.style.fontSize = '13px';
  cont.style.color = '#000000';
  cont.innerHTML = tkGenerarHTML(tkActual);
  cont.querySelectorAll('.tk-sub, .tk-foot, .tk-line, .tk-total').forEach(function(el){ el.style.color = '#000000'; });
  cont.querySelectorAll('.tk-desc').forEach(function(el){ el.style.color = '#a32d2d'; });
  document.body.appendChild(cont);
  try{
    await new Promise(function(r){ setTimeout(r, 80); });
    const canvas = await html2canvas(cont, {scale:2, backgroundColor:'#ffffff', useCORS:true});
    const img = canvas.toDataURL('image/png');
    const w = 320, h = (canvas.height * w) / canvas.width;
    const doc = new jsPDFCtor({unit:'pt', format:[w, h], orientation:'portrait'});
    doc.addImage(img, 'PNG', 0, 0, w, h);
    return doc.output('blob');
  } finally {
    document.body.removeChild(cont);
  }
}

async function tkDescargar(){
  if(!tkActual) return;
  const blob = await tkGenerarPDF();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'devolucion_' + tkActual.id + '.pdf';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 3000);
}

async function tkCompartirWhatsApp(){
  if(!tkActual) return;
  const blob = await tkGenerarPDF();
  const archivo = new File([blob], 'devolucion_' + tkActual.id + '.pdf', {type:'application/pdf'});
  if(navigator.canShare && navigator.canShare({files:[archivo]})){
    try{ await navigator.share({files:[archivo]}); return; }
    catch(e){ if(e.name === 'AbortError') return; }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'devolucion_' + tkActual.id + '.pdf';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 3000);
  alert('Tu navegador no permite compartir directo. Se descargó el PDF: adjúntalo manualmente en WhatsApp.');
}

function tkImprimir(){
  if(!tkActual) return;
  const win = window.open('', '_blank');
  const estilos = '<style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto;color:#000}'
    + '.tk-head,.tk-foot{text-align:center;margin:8px 0}.tk-sub{font-size:12px;color:#000;text-align:center}'
    + '.tk-line{display:flex;justify-content:space-between;margin-bottom:3px}'
    + '.tk-desc{color:#a32d2d}'
    + '.tk-total{font-weight:700;font-size:16px;margin-top:8px;padding-top:8px}</style>';
  win.document.write('<html><head><title>Comprobante de devolución</title>' + estilos + '</head><body>' + tkGenerarHTML(tkActual) + '</body></html>');
  win.document.close();
  setTimeout(function(){ win.print(); }, 300);
}
'''
    m = re.search(r'</script>\s*(?:<!--[^>]*-->\s*)?</body>', src)
    if m:
        src = src[:m.start()] + js + src[m.start():]
        res.append("OK: funciones del ticket agregadas")
    else:
        i = src.rfind('</script>')
        if i != -1:
            src = src[:i] + js + src[i:]
            res.append("OK: funciones del ticket agregadas (fallback)")
        else:
            res.append("ERROR: no se encontro donde insertar el JS")
else:
    res.append("* las funciones del ticket ya existian")

# ============================================================
# 5. Mostrar el ticket al confirmar
# ============================================================
viejo = '''    document.getElementById('num-ticket').value = ventaActual.id;
    buscarVentaSilencioso();'''
nuevo = '''    document.getElementById('num-ticket').value = ventaActual.id;
    buscarVentaSilencioso();
    if(data.id_devolucion) tkMostrar(data.id_devolucion, !esDevolucion);'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK: el ticket se muestra al confirmar")
elif 'tkMostrar(data.id_devolucion' in src:
    res.append("* ya se mostraba el ticket")
else:
    res.append("ERROR: no se encontro el final de confirmarMotivo")

open(DEV, 'w', encoding='utf-8').write(src)

# ============================================================
print()
for r in res:
    print(r)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves en devoluciones.html:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Haz una devolucion nueva: al confirmar debe aparecer")
    print("el comprobante con los botones WhatsApp / Descargar / Imprimir.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
