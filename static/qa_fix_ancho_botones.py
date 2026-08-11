#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Iguala el ancho de los botones (WhatsApp vs Descargar/Imprimir) y
quita los iconos de Descargar/Imprimir.
Aplica a pagos.html y historial.html.
Uso: cd ~/inventario-qa/static && python3 qa_fix_ancho_botones.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

# ================================================================
# PAGOS.HTML
# ================================================================
pagos_path = os.path.join(STATIC, 'pagos.html')
src = open(pagos_path, encoding='utf-8').read()
original = src

viejo_pagos = '''    <div class="acciones" style="flex-direction:column;gap:8px">
      <button onclick="compartirWhatsApp()" style="width:100%;height:50px;border-radius:12px;border:none;background:#25d366;color:#fff;font-weight:700;font-size:15px;cursor:pointer">Compartir por WhatsApp</button>
      <div style="display:flex;gap:8px">
        <button onclick="descargarTicket()" style="flex:1;height:38px;border-radius:8px;border:0.5px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer">⬇ Descargar</button>
        <button onclick="imprimirTicket()" style="flex:1;height:38px;border-radius:8px;border:0.5px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer">🖨 Imprimir</button>
      </div>
    </div>'''

nuevo_pagos = '''    <div style="display:flex;flex-direction:column;gap:8px;width:100%;box-sizing:border-box">
      <button onclick="compartirWhatsApp()" style="display:block;width:100%;box-sizing:border-box;height:50px;border-radius:12px;border:none;background:#25d366;color:#fff;font-weight:700;font-size:15px;cursor:pointer">Compartir por WhatsApp</button>
      <div style="display:flex;gap:8px;width:100%;box-sizing:border-box">
        <button onclick="descargarTicket()" style="flex:1;height:38px;border-radius:8px;border:0.5px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer">Descargar</button>
        <button onclick="imprimirTicket()" style="flex:1;height:38px;border-radius:8px;border:0.5px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer">Imprimir</button>
      </div>
    </div>'''

n1 = src.count(viejo_pagos)
if n1 == 1:
    src = src.replace(viejo_pagos, nuevo_pagos, 1)
    print("1. pagos.html: ancho igualado, iconos quitados")
elif 'display:flex;flex-direction:column;gap:8px;width:100%;box-sizing:border-box' in src:
    print("1. * pagos.html: ya estaba actualizado")
else:
    print("1. ERROR: no se encontro el bloque exacto en pagos.html")

if src != original:
    open(pagos_path, 'w', encoding='utf-8').write(src)

scripts_pagos = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok_pagos = all(s.count('{') == s.count('}') for s in scripts_pagos)
print("   Balance de llaves en pagos.html:", "OK" if ok_pagos else "DESBALANCEADO")

# ================================================================
# HISTORIAL.HTML
# ================================================================
hist_path = os.path.join(STATIC, 'historial.html')
src2 = open(hist_path, encoding='utf-8').read()
original2 = src2

viejo_hist = '''      <button onclick="compartirWhatsApp()" style="border:none;background:#25d366;color:#fff;font-weight:700;flex:1.4">Compartir por WhatsApp</button>
      <button onclick="descargarTicketDetalle()" style="color:var(--text2);font-size:13px">⬇ Descargar</button>
      <button onclick="imprimirDetalle()" style="color:var(--text2);font-size:13px">🖨 Imprimir</button>'''

nuevo_hist = '''      <button onclick="compartirWhatsApp()" style="width:100%;border:none;background:#25d366;color:#fff;font-weight:700;flex-basis:100%">Compartir por WhatsApp</button>
      <button onclick="descargarTicketDetalle()" style="flex:1;color:var(--text2);font-size:13px">Descargar</button>
      <button onclick="imprimirDetalle()" style="flex:1;color:var(--text2);font-size:13px">Imprimir</button>'''

n2 = src2.count(viejo_hist)
if n2 == 1:
    src2 = src2.replace(viejo_hist, nuevo_hist, 1)
    print("2. historial.html: ancho igualado, iconos quitados")
elif 'flex-basis:100%' in src2:
    print("2. * historial.html: ya estaba actualizado")
else:
    print("2. ERROR: no se encontro el bloque exacto en historial.html")

if src2 != original2:
    open(hist_path, 'w', encoding='utf-8').write(src2)

scripts_hist = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src2, re.DOTALL)
ok_hist = all(s.count('{') == s.count('}') for s in scripts_hist)
print("   Balance de llaves en historial.html:", "OK" if ok_hist else "DESBALANCEADO")

print()
print("=" * 55)
if ok_pagos and ok_hist:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Los botones ahora deberian tener el mismo ancho, sin iconos")
    print("en Descargar/Imprimir.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
