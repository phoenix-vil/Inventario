#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega el diagnostico de consola en pagos.html e historial.html,
usando un patron regex flexible (tolera variaciones de espacios/saltos
de linea) en vez de coincidencia de texto literal exacta.
Uso: cd ~/inventario-qa/static && python3 qa_diagnostico_v2.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
archivos = ['pagos.html', 'historial.html']

patron = re.compile(
    r"if\(navigator\.canShare\s*&&\s*navigator\.canShare\(\{files:\[archivo\]\}\)\)\{\s*"
    r"try\{\s*await navigator\.share\(\{files:\[archivo\]\}\);\s*return;\s*\}\s*"
    r"catch\(e\)\{\s*if\(e\.name\s*===\s*'AbortError'\)\s*return;\s*\}\s*"
    r"\}"
)

reemplazo = '''const puedeCompartir = navigator.canShare && navigator.canShare({files:[archivo]});
  console.log('[diagnostico compartir]', nombreArchivo, '| canShare:', puedeCompartir, '| tamano:', archivo.size, 'bytes | tipo:', archivo.type);
  if(puedeCompartir){
    try{
      await navigator.share({files:[archivo]});
      return;
    }catch(e){
      console.log('[diagnostico compartir] navigator.share fallo:', e.name, e.message);
      if(e.name === 'AbortError') return;
    }
  }'''

total_ok = 0
for nombre in archivos:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        print(nombre + ": no existe, se omite")
        continue
    src = open(ruta, encoding='utf-8').read()

    if '[diagnostico compartir]' in src:
        print("* " + nombre + ": el diagnostico ya existia")
        continue

    nueva_src, n = patron.subn(reemplazo, src, count=1)
    if n == 1:
        open(ruta, 'w', encoding='utf-8').write(nueva_src)
        print("OK " + nombre + ": diagnostico agregado")
        total_ok += 1
    else:
        print("ERROR " + nombre + ": el patron regex no coincidio (coincidencias: " + str(n) + ")")

print()
print("Total actualizado: " + str(total_ok) + " archivo(s)")
print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. Prueba de nuevo compartir el ticket de venta y pegame")
print("las lineas que empiecen con '[diagnostico compartir]' de la consola.")
