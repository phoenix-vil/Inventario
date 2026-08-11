#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Pulido final de devoluciones:
 1. Botones del comprobante centrados y homologados
 2. Ticket con desglose: precio original -> descuento por item ->
    subtotal -> descuento general -> total devuelto
 3. Estilos .field (faltaban por completo, por eso la etiqueta salia
    pegada al campo) + lista fija de motivos en vez de texto libre
Uso: cd ~/inventario-qa/static && python3 qa_devoluciones_pulido.py
"""
import os, re

DEV = os.path.expanduser('~/inventario-qa/static/devoluciones.html')
src = open(DEV, encoding='utf-8').read()
res = []

# ============================================================
# 1. Estilos: .field (faltaba) + botones del comprobante
# ============================================================
viejo_css = '''.tk-botones{display:flex;flex-direction:column;gap:8px}
.tk-botones .fila{display:flex;gap:8px}
.tk-btn-wa{width:100%;height:46px;border:none;border-radius:10px;background:#25D366;color:#fff;font-weight:700;font-size:15px;cursor:pointer}
.tk-btn-sec{flex:1;height:44px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-weight:600;font-size:14px;cursor:pointer;box-sizing:border-box}'''
nuevo_css = '''.tk-botones{display:flex;flex-direction:column;gap:8px;width:100%}
.tk-botones .fila{display:flex;gap:8px;width:100%}
.tk-btn-wa{width:100%;height:46px;border:none;border-radius:10px;background:#25D366;color:#fff;font-weight:700;font-size:15px;cursor:pointer;box-sizing:border-box}
.tk-btn-sec{flex:1 1 0;height:44px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-weight:600;font-size:14px;cursor:pointer;box-sizing:border-box}
.tk-btn-cerrar{width:100%;height:40px;border:none;background:transparent;color:var(--text2);font-size:14px;cursor:pointer;text-align:center}
.field{margin-bottom:14px}
.field label{display:block;font-size:12px;color:var(--text2);margin-bottom:5px}
.field input,.field select{width:100%;height:44px;padding:0 12px;border:0.5px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);font-size:15px;box-sizing:border-box}'''
if viejo_css in src:
    src = src.replace(viejo_css, nuevo_css, 1)
    res.append("OK: estilos .field agregados y botones del comprobante ajustados")
elif '.field label{display:block' in src:
    res.append("* los estilos ya estaban")
else:
    res.append("ERROR: no se encontro el bloque de estilos del comprobante")

# ============================================================
# 2. Botón Cerrar del comprobante (fuera de la fila)
# ============================================================
viejo_b = '''      <div class="fila">
        <button class="tk-btn-sec" onclick="tkCerrar()">Cerrar</button>
      </div>'''
nuevo_b = '''      <button class="tk-btn-cerrar" onclick="tkCerrar()">Cerrar</button>'''
if viejo_b in src:
    src = src.replace(viejo_b, nuevo_b, 1)
    res.append("OK: boton Cerrar del comprobante ajustado")
elif 'tk-btn-cerrar' in src:
    res.append("* el boton Cerrar ya estaba ajustado")

# ============================================================
# 3. Motivo: lista fija en vez de texto libre
# ============================================================
viejo_m = '''    <div class="field"><label>Motivo (obligatorio)</label><input type="text" id="motivo-input" placeholder="Ej: producto defectuoso" autocomplete="off"></div>'''
nuevo_m = '''    <div class="field"><label>Motivo (obligatorio)</label>
      <select id="motivo-input">
        <option value="">Selecciona un motivo...</option>
        <option value="Producto defectuoso">Producto defectuoso</option>
        <option value="Producto equivocado">Producto equivocado</option>
        <option value="No era lo que esperaba">No era lo que esperaba</option>
        <option value="Error de cobro">Error de cobro</option>
        <option value="Error de captura">Error de captura</option>
        <option value="Cliente cambio de opinion">Cliente cambió de opinión</option>
        <option value="Otro">Otro</option>
      </select>
    </div>'''
if viejo_m in src:
    src = src.replace(viejo_m, nuevo_m, 1)
    res.append("OK: motivo ahora es una lista de 7 opciones")
elif '<select id="motivo-input">' in src:
    res.append("* el motivo ya era una lista")
else:
    res.append("ADVERTENCIA: no se encontro el campo de motivo")

# --- limpiar el valor al abrir el modal ---
if "document.getElementById('motivo-input').value = ''" not in src:
    m = re.search(r"(document\.getElementById\('motivo-modal'\)\.classList\.add\('open'\);)", src)
    if m:
        src = src[:m.start()] + "document.getElementById('motivo-input').value = '';\n  " + src[m.start():]
        res.append("OK: el motivo se limpia al abrir el modal")

# ============================================================
# 4. Ticket con desglose completo
# ============================================================
inicio = src.find('function tkGenerarHTML(v){')
if inicio == -1:
    res.append("ERROR: no se encontro tkGenerarHTML")
else:
    prof = 0
    enc = False
    fin = -1
    for i in range(inicio, len(src)):
        c = src[i]
        if c == '{':
            prof += 1; enc = True
        elif c == '}':
            prof -= 1
            if enc and prof == 0:
                fin = i + 1
                break
    if fin == -1:
        res.append("ERROR: no se pudo delimitar tkGenerarHTML")
    else:
        nueva = '''function tkGenerarHTML(v){
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
}'''
        src = src[:inicio] + nueva + src[fin:]
        res.append("OK: ticket con desglose (original, desc. por item, general, total)")

open(DEV, 'w', encoding='utf-8').write(src)

# ============================================================
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
    print("Listo. Ctrl+Shift+R y prueba una devolucion nueva.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
