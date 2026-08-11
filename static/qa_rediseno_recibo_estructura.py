#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Rediseña generarReciboHTML para que siga la MISMA estructura que
el ticket de venta: bloque centrado (Cliente/fecha/Atendio/Sucursal)
debajo del logo, luego tabla de datos (Monto/Metodo), luego Saldo.
Uso: cd ~/inventario-qa/static && python3 qa_rediseno_recibo_estructura.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario-qa/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()

inicio = src.find('function generarReciboHTML(v){')
if inicio == -1:
    print("ERROR: no se encontro generarReciboHTML")
else:
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
        print("ERROR: no se pudo determinar el cierre de la funcion")
    else:
        nueva_funcion = '''function generarReciboHTML(v){
  const fecha = new Date(v.fecha).toLocaleString('es-MX').replace(',', '');
  const logoSrc = _logoCacheDataUrl || '/static/logo.png';
  const RAYA = '<svg width="100%" height="3" style="display:block;margin:6px 0"><line x1="0" y1="1.5" x2="100%" y2="1.5" stroke="#000" stroke-width="1" stroke-dasharray="4,3"/></svg>';
  let html = `<div class="tk-head">
    <img src="${logoSrc}" alt="Only Enterprises" style="height:44px;width:auto;margin-bottom:6px">
    <div class="tk-sub">Recibo de abono</div>
    <div class="tk-sub">Cliente: ${esc(v.cliente_nombre)}</div>
    <div class="tk-sub">${fecha}</div>
    ${v.operador?`<div class="tk-sub">Atendió: ${esc(v.operador)}</div>`:''}
    ${v.sucursal?`<div class="tk-sub">Sucursal: ${esc(v.sucursal)}</div>`:''}
  </div>${RAYA}`;
  html += `<div class="tk-line"><span>Monto abonado</span><span>${money(v.monto)}</span></div>`;
  html += `<div class="tk-line"><span>Método</span><span>${esc(v.metodo_pago)}</span></div>`;
  if(v.nota) html += `<div class="tk-line"><span>Nota</span><span>${esc(v.nota)}</span></div>`;
  html += RAYA;
  html += `<div class="tk-line tk-total"><span>Saldo restante</span><span>${money(v.saldo_restante)}</span></div>`;
  html += '<div class="tk-foot">¡Gracias por su pago!</div>';
  return html;
}'''

        src = src[:inicio] + nueva_funcion + src[fin:]
        open(CLIENTES, 'w', encoding='utf-8').write(src)
        print("OK: generarReciboHTML rediseñada con la misma estructura del ticket de venta")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El recibo ahora tiene: logo, bloque centrado (Recibo de abono /")
    print("Cliente / fecha / Atendio / Sucursal), linea punteada, tabla de Monto/Metodo,")
    print("linea punteada, Saldo restante, y el pie de pagina.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
