#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Redisena el boton de descuento por item (de emoji tenue a boton
cuadrado con fondo verde y simbolo "%"), y le da el mismo tratamiento
visual al boton de eliminar (fondo rojo tenue) para que ambos tengan
el mismo peso visual.
Uso: cd ~/inventario-qa/static && python3 qa_rediseno_boton_descuento.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. CSS: botones cuadrados con fondo, en vez de iconos planos
# ================================================================
viejo_css_del = '.ci-del{background:none;border:none;color:var(--red);cursor:pointer;font-size:16px;padding:4px}'
nuevo_css_del = '.ci-del{width:34px;height:34px;border-radius:9px;border:0.5px solid var(--red-bg);background:var(--red-bg);color:var(--red);font-size:15px;cursor:pointer;flex-shrink:0}'

viejo_css_desc = '.ci-desc-btn{background:none;border:none;color:var(--blue);cursor:pointer;font-size:15px;padding:4px}'
nuevo_css_desc = '.ci-desc-btn{width:34px;height:34px;border-radius:9px;border:0.5px solid var(--green-bg);background:var(--green-bg);color:var(--green);font-size:15px;font-weight:700;cursor:pointer;flex-shrink:0}'

if viejo_css_del in src:
    src = src.replace(viejo_css_del, nuevo_css_del, 1)
    cambios.append('CSS .ci-del rediseñado (fondo rojo tenue)')
elif 'width:34px;height:34px;border-radius:9px;border:0.5px solid var(--red-bg)' in src:
    cambios.append('* .ci-del ya estaba rediseñado')

if viejo_css_desc in src:
    src = src.replace(viejo_css_desc, nuevo_css_desc, 1)
    cambios.append('CSS .ci-desc-btn rediseñado (fondo verde, cuadrado)')
elif 'width:34px;height:34px;border-radius:9px;border:0.5px solid var(--green-bg)' in src:
    cambios.append('* .ci-desc-btn ya estaba rediseñado')

# ================================================================
# 2. HTML: cambiar el emoji 🏷 por el simbolo "%"
# ================================================================
viejo_html = '<button class="ci-desc-btn" onclick="descuentoItem(${c.id})" title="Descuento a este artículo">🏷</button>'
nuevo_html = '<button class="ci-desc-btn" onclick="descuentoItem(${c.id})" title="Descuento a este artículo">%</button>'

if viejo_html in src:
    src = src.replace(viejo_html, nuevo_html, 1)
    cambios.append('emoji 🏷 cambiado por simbolo %')
elif 'title="Descuento a este artículo">%</button>' in src:
    cambios.append('* ya usaba el simbolo %')

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
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
    print("Listo. El boton de descuento por articulo ahora es un cuadrado")
    print("verde con '%', y el de eliminar tiene el mismo estilo en rojo.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
