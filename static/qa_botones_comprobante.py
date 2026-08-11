#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Centra el texto dentro de los botones del comprobante y le pone
    marco al boton Cerrar (los botones de la app son flex, por eso
    text-align no bastaba: faltaba justify-content).
 2. Corrige el texto tenue bajo el logo: el comprobante tiene fondo
    blanco fijo, pero las clases usaban var(--text), que en modo oscuro
    resuelve a un color claro y casi no se ve.
Uso: cd ~/inventario-qa/static && python3 qa_botones_comprobante.py
"""
import os, re

DEV = os.path.expanduser('~/inventario-qa/static/devoluciones.html')
src = open(DEV, encoding='utf-8').read()
res = []

# ============================================================
# 1. Botones: centrado real + marco en Cerrar
# ============================================================
viejo = '''.tk-btn-wa{width:100%;height:46px;border:none;border-radius:10px;background:#25D366;color:#fff;font-weight:700;font-size:15px;cursor:pointer;box-sizing:border-box}
.tk-btn-sec{flex:1 1 0;height:44px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-weight:600;font-size:14px;cursor:pointer;box-sizing:border-box}
.tk-btn-cerrar{width:100%;height:40px;border:none;background:transparent;color:var(--text2);font-size:14px;cursor:pointer;text-align:center}'''
nuevo = '''.tk-btn-wa{width:100%;height:46px;border:none;border-radius:10px;background:#25D366;color:#fff;font-weight:700;font-size:15px;cursor:pointer;box-sizing:border-box;display:flex;align-items:center;justify-content:center;text-align:center}
.tk-btn-sec{flex:1 1 0;height:44px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-weight:600;font-size:14px;cursor:pointer;box-sizing:border-box;display:flex;align-items:center;justify-content:center;text-align:center}
.tk-btn-cerrar{width:100%;height:44px;border:0.5px solid var(--border);border-radius:10px;background:transparent;color:var(--text);font-weight:600;font-size:14px;cursor:pointer;box-sizing:border-box;display:flex;align-items:center;justify-content:center;text-align:center}'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    res.append("OK: texto centrado en los 3 botones y marco en Cerrar")
elif '.tk-btn-cerrar{width:100%;height:44px;border:0.5px solid' in src:
    res.append("* los botones ya estaban corregidos")
else:
    res.append("ERROR: no se encontro el bloque de estilos de los botones")

# ============================================================
# 2. Texto del comprobante siempre negro (fondo blanco fijo)
# ============================================================
viejo2 = '''.tk-head,.tk-foot{text-align:center;margin:8px 0}
.tk-sub{font-size:12px;color:var(--text);text-align:center}'''
nuevo2 = '''.tk-head,.tk-foot{text-align:center;margin:8px 0}
.tk-sub{font-size:12px;color:#000;text-align:center}
#tk-contenido,#tk-contenido .tk-line,#tk-contenido .tk-total,#tk-contenido .tk-foot,#tk-contenido .tk-head{color:#000}
#tk-contenido .tk-desc{color:#a32d2d}'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    res.append("OK: el texto del comprobante ya no depende del modo oscuro")
elif '#tk-contenido,#tk-contenido .tk-line' in src:
    res.append("* el color del comprobante ya estaba corregido")
else:
    res.append("ADVERTENCIA: no se encontro el bloque .tk-sub")

open(DEV, 'w', encoding='utf-8').write(src)

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
    print("Listo. Ctrl+Shift+R y abre un comprobante.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
