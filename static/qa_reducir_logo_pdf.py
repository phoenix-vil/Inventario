#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Redimensiona el logo a un tamano chico ANTES de convertirlo a base64,
para que el PDF pese lo que debe pesar (unos pocos KB, no ~1.7MB).
jsPDF incrusta la imagen a su resolucion de archivo completa, sin importar
el tamano de dibujo que le pidamos, asi que hay que reducirla nosotros.
Aplica a pagos.html, historial.html y clientes.html.
Uso: cd ~/inventario-qa/static && python3 qa_reducir_logo_pdf.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
archivos = ['pagos.html', 'historial.html', 'clientes.html']

viejo = '''let _logoCacheDataUrl = null;
function cargarImagenBase64(url){
  if(_logoCacheDataUrl){
    return Promise.resolve(_logoCacheDataUrl);
  }
  return new Promise(function(resolve, reject){
    fetch(url).then(function(r){ return r.blob(); }).then(function(blob){
      const reader = new FileReader();
      reader.onloadend = function(){
        _logoCacheDataUrl = reader.result;
        resolve(reader.result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    }).catch(reject);
  });
}'''

nuevo = '''let _logoCacheDataUrl = null;
function cargarImagenBase64(url){
  if(_logoCacheDataUrl){
    return Promise.resolve(_logoCacheDataUrl);
  }
  return new Promise(function(resolve, reject){
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function(){
      const anchoDestino = 240;
      const alto = Math.round(img.height * (anchoDestino / img.width));
      const canvas = document.createElement('canvas');
      canvas.width = anchoDestino;
      canvas.height = alto;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, anchoDestino, alto);
      const dataUrl = canvas.toDataURL('image/png');
      _logoCacheDataUrl = dataUrl;
      resolve(dataUrl);
    };
    img.onerror = reject;
    img.src = url;
  });
}'''

total_ok = 0
for nombre in archivos:
    ruta = os.path.join(STATIC, nombre)
    if not os.path.exists(ruta):
        print(nombre + ": no existe, se omite")
        continue
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": logo se redimensiona a 240px de ancho antes de usarse")
        total_ok += 1
    elif 'anchoDestino = 240' in src:
        print("* " + nombre + ": ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro cargarImagenBase64 con cache exacto")

print()
print("Total actualizado: " + str(total_ok) + " archivo(s)")
print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. El PDF ahora deberia pesar unos pocos KB en vez de 1.7MB.")
print("Recarga la pagina por completo (Ctrl+Shift+R) antes de probar,")
print("para que el cache viejo del logo (el grande) se descarte.")
