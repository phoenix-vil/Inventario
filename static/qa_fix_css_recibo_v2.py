#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Inserta el CSS de tickets justo antes de </head> (verificado con
precision esta vez, ignorando coincidencias falsas dentro de strings JS).
Uso: cd ~/inventario-qa/static && python3 qa_fix_css_recibo_v2.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario-qa/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()

# Verificar de forma precisa: buscar el CSS SOLO en la seccion <head>
idx_head_fin = src.find('</head>')
seccion_head = src[:idx_head_fin] if idx_head_fin != -1 else src

if '.tk-line{' in seccion_head:
    print("* El CSS ya existia en el <head>, no se hace nada")
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
    if idx_head_fin != -1:
        src = src[:idx_head_fin] + css_tickets + src[idx_head_fin:]
        open(CLIENTES, 'w', encoding='utf-8').write(src)
        print("OK: CSS de tickets insertado justo antes de </head>")
    else:
        print("ERROR: no se encontro </head> en el archivo")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Refresca con Ctrl+Shift+R y prueba de nuevo el recibo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
