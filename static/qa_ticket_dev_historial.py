#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Al abrir una devolucion desde el historial, el ticket se mostraba
con formato de venta ("Ticket de venta", "Gracias por su compra").
Se agrega una rama al inicio de ticketHTML para que las devoluciones
usen su propio formato -- asi aplica tambien a PDF, impresion y WhatsApp.
Tambien ajusta el titulo del modal de detalle.
Uso: cd ~/inventario-qa/static && python3 qa_ticket_dev_historial.py
"""
import os, re

HIST = os.path.expanduser('~/inventario-qa/static/historial.html')
src = open(HIST, encoding='utf-8').read()
res = []

# ============================================================
# 1. Helper con el formato de devolucion
# ============================================================
if 'function ticketDevolucionHTML' not in src:
    helper = '''function ticketDevolucionHTML(v){
  const fecha = new Date(v.fecha).toLocaleString('es-MX').replace(',', '');
  const logoSrc = (typeof _logoCacheDataUrl !== 'undefined' && _logoCacheDataUrl) ? _logoCacheDataUrl : '/static/logo.png';
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

  let subtotalNeto = 0;
  (v.detalle || []).forEach(function(it){
    const cant = Math.abs(it.cantidad);
    const c = Number.isInteger(cant) ? cant + 'x' : cant.toFixed(3) + 'kg';
    const pUnit = it.precio_unitario || 0;
    const pOrig = (it.precio_original != null && it.precio_original > pUnit) ? it.precio_original : pUnit;
    subtotalNeto += pUnit * cant;
    html += '<div class="tk-line"><span>' + c + ' ' + esc(it.nombre) + '</span><span>' + money(pOrig * cant) + '</span></div>';
    if(pOrig > pUnit){
      const pct = Math.round((1 - pUnit / pOrig) * 100);
      html += '<div class="tk-line tk-desc"><span style="padding-left:12px">Descuento (' + pct + '%)</span><span>'
        + money(-((pOrig - pUnit) * cant)) + '</span></div>';
    }
  });
  html += RAYA;

  const pctGen = v.descuento_extra_pct || 0;
  if(pctGen > 0){
    html += '<div class="tk-line"><span>Subtotal devuelto</span><span>' + money(subtotalNeto) + '</span></div>';
    html += '<div class="tk-line tk-desc"><span>Descuento general (' + fmtPct(pctGen) + '%)</span><span>'
      + money(-(subtotalNeto * pctGen / 100)) + '</span></div>';
    html += RAYA;
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

'''
    i = src.find('function ticketHTML(v){')
    if i == -1:
        res.append("ERROR: no se encontro ticketHTML")
    else:
        src = src[:i] + helper + src[i:]
        res.append("OK: helper ticketDevolucionHTML agregado")
else:
    res.append("* el helper ya existia")

# ============================================================
# 2. Rama al inicio de ticketHTML
# ============================================================
viejo = 'function ticketHTML(v){\n'
nuevo = ('function ticketHTML(v){\n'
         "  if(v && ((v.estado === 'devolucion') || (v.total < 0))) return ticketDevolucionHTML(v);\n")
if "if(v && ((v.estado === 'devolucion')" not in src:
    if viejo in src:
        src = src.replace(viejo, nuevo, 1)
        res.append("OK: ticketHTML deriva las devoluciones a su formato")
    else:
        res.append("ERROR: no se encontro la firma de ticketHTML")
else:
    res.append("* la rama ya existia")

# ============================================================
# 3. Titulo del modal de detalle
# ============================================================
viejo_t = "  document.getElementById('detalle-contenido').innerHTML=ticketHTML(ventaDetalle);"
nuevo_t = ("  const _esDev = ventaDetalle && ((ventaDetalle.estado === 'devolucion') || (ventaDetalle.total < 0));\n"
           "  const _tit = document.querySelector('#detalle-modal h2');\n"
           "  if(_tit) _tit.textContent = _esDev ? 'Detalle de devolución' : 'Detalle de venta';\n"
           "  document.getElementById('detalle-contenido').innerHTML=ticketHTML(ventaDetalle);")
if viejo_t in src:
    src = src.replace(viejo_t, nuevo_t, 1)
    res.append("OK: el titulo del modal cambia segun el tipo")
elif "_tit.textContent = _esDev" in src:
    res.append("* el titulo ya cambiaba")
else:
    res.append("ADVERTENCIA: no se encontro la asignacion de detalle-contenido")

open(HIST, 'w', encoding='utf-8').write(src)

print()
for r in res:
    print(r)

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and not any(r.startswith('ERROR') for r in res):
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Abre una devolucion desde el historial y prueba tambien")
    print("Descargar / Imprimir / WhatsApp desde ahi.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
