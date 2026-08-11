#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Quita el emoji roto del boton de WhatsApp (se veia como un punto
blanco en vez del icono). El texto queda solo, sin simbolo.
Aplica a pagos.html y historial.html.
Uso: cd ~/inventario-qa/static && python3 qa_fix_boton_whatsapp.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

cambios_txt = [
    ('>💬 Compartir por WhatsApp<', '>Compartir por WhatsApp<'),
]

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        print(nombre + ": no existe, se omite")
        continue
    src = open(ruta, encoding='utf-8').read()
    original = src
    for viejo, nuevo in cambios_txt:
        n = src.count(viejo)
        if n >= 1:
            src = src.replace(viejo, nuevo)
            print("OK " + nombre + ": emoji quitado (" + str(n) + " ocurrencia(s))")
            total += n
    if src != original:
        open(ruta, 'w', encoding='utf-8').write(src)
    elif 'Compartir por WhatsApp<' in src and '💬' not in src:
        print("* " + nombre + ": ya estaba sin el emoji")
    else:
        print("ERROR " + nombre + ": no se encontro el texto exacto del boton")

print()
print("Total corregido: " + str(total))
print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. El boton ahora dice solo 'Compartir por WhatsApp', sin simbolo.")
