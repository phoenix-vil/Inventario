#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega el CSS de los tickets (.tk-line, .tk-sub, etc.) que se
quedo sin insertar en clientes.html por el ?v=... en el link de modern.css.
Uso: cd ~/inventario-qa/static && python3 qa_fix_css_recibo.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario-qa/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()

if '.tk-line{' in src:
    print("* El CSS ya existia, no se hace nada")
else:
    css_tickets = '''<style>
.tk-head,.tk-foot{text-align:center;margin:8px 0}
.tk-sub{font-size:12px;color:#000}
.tk-items{padding:8px 0;margin:8px 0}
.tk-line{display:flex;justify-content:space-between;margin-bottom:3px}
.tk-total{font-weight:700;font-size:16px;margin-top:8px;padding-top:8px}
.tk-desc{color:#a32d2d}
.tk-ahorro{color:#3b6d11;font-weight:bold}
</style>
'''
    patron = re.compile(r'<link rel="stylesheet" href="/static/modern\.css[^"]*">')
    nueva_src, n = patron.subn(lambda m: css_tickets + m.group(0), src, count=1)
    if n == 1:
        src = nueva_src
        open(CLIENTES, 'w', encoding='utf-8').write(src)
        print("OK: CSS de tickets agregado (con patron flexible para el ?v=...)")
    else:
        print("ERROR: no se encontro el link de modern.css ni con el patron flexible")
        print("Coincidencias encontradas: " + str(n))

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El recibo deberia verse con el formato de tabla correcto ahora.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
