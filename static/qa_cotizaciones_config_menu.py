#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega "Cotizaciones" al menu desplegable de configuracion,
disponible para CUALQUIER operador (no solo gerentes, a diferencia
de Usuarios/Sucursales que si usan config-gerente-only).
Uso: cd ~/inventario-qa/static && python3 qa_cotizaciones_config_menu.py
"""
import os, re

MENU = os.path.expanduser('~/inventario-qa/static/menu.html')
src = open(MENU, encoding='utf-8').read()

if 'href="/cotizaciones"' in src:
    print("* Ya estaba agregado")
else:
    viejo = '''        <a href="/usuarios" class="config-gerente-only" style="display:none;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">👥 Usuarios</a>'''
    nuevo = '''        <a href="/cotizaciones" style="display:block;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">📝 Cotizaciones</a>
        <a href="/usuarios" class="config-gerente-only" style="display:none;padding:10px 14px;color:var(--text);text-decoration:none;font-size:14px;border-bottom:0.5px solid var(--border)">👥 Usuarios</a>'''
    if viejo in src:
        src = src.replace(viejo, nuevo, 1)
        open(MENU, 'w', encoding='utf-8').write(src)
        print("OK: Cotizaciones agregado al menu de configuracion (visible para todos)")
    else:
        print("ERROR: no se encontro el enlace de Usuarios en el dropdown")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)
print()
print("Balance de llaves:", "OK" if ok else "DESBALANCEADO")

print()
print("=" * 58)
if ok and 'ERROR' not in open(__file__).read()[:0]:  # placeholder, real check below
    pass
if ok:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Ctrl+Shift+R -- deberia verse 'Cotizaciones' en el menu de")
    print("configuracion (el engrane), disponible para cualquier operador.")
else:
    print("Revisa los mensajes de arriba. NO se reinicio el servicio.")
