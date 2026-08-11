#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] 1. Corrige la descarga de respaldo (no revocar el blob tan rapido).
2. Agrega un diagnostico temporal en consola para ver EXACTAMENTE por
   que navigator.share() rechaza el archivo de venta.
Aplica a pagos.html, historial.html y clientes.html.
Uso: cd ~/inventario-qa/static && python3 qa_fix_descarga_y_diagnostico.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
archivos = ['pagos.html', 'historial.html', 'clientes.html']

viejo = '''  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nombreArchivo;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  alert('Tu navegador no permite compartir directo. Se descargó el PDF: adjúntalo manualmente en WhatsApp.');
}'''

nuevo = '''  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nombreArchivo;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 3000);
  alert('Tu navegador no permite compartir directo. Se descargó el PDF: adjúntalo manualmente en WhatsApp.');
}'''

total_ok = 0
for nombre in archivos:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        print(nombre + ": no existe, se omite")
        continue
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n >= 1:
        src = src.replace(viejo, nuevo)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": revocacion del blob retrasada 3 seg (" + str(n) + " ocurrencia(s))")
        total_ok += 1
    elif 'setTimeout(function(){ URL.revokeObjectURL' in src:
        print("* " + nombre + ": ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto")

print()

# ================================================================
# Diagnostico: mostrar en consola por que fallo canShare/share
# ================================================================
viejo_diag = '''  if(navigator.canShare && navigator.canShare({files:[archivo]})){
    try{
      await navigator.share({files:[archivo]});
      return;
    }catch(e){
      if(e.name === 'AbortError') return;
    }
  }'''

nuevo_diag = '''  const puedeCompartir = navigator.canShare && navigator.canShare({files:[archivo]});
  console.log('[diagnostico compartir] canShare files:', puedeCompartir, '| tamano archivo:', archivo.size, 'bytes | tipo:', archivo.type);
  if(puedeCompartir){
    try{
      await navigator.share({files:[archivo]});
      return;
    }catch(e){
      console.log('[diagnostico compartir] navigator.share fallo:', e.name, e.message);
      if(e.name === 'AbortError') return;
    }
  }'''

for nombre in archivos:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        continue
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo_diag)
    if n >= 1:
        src = src.replace(viejo_diag, nuevo_diag)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": diagnostico agregado (" + str(n) + " ocurrencia(s))")
    elif '[diagnostico compartir]' in src:
        print("* " + nombre + ": diagnostico ya existia")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque de canShare/share exacto")

print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. Prueba de nuevo compartir el ticket de venta, y esta vez")
print("pegame lo que salga en la consola con el prefijo '[diagnostico compartir]'.")
print("Ese mensaje va a decir el tamano exacto del PDF y el error real de navigator.share.")
