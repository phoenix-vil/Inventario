#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Cachea el logo en memoria tras la primera carga, para que compartir
por WhatsApp sea mas rapido y no pierda el permiso de "gesto del usuario"
en navegadores como Windows/Edge (que exigen compartir casi al instante
del clic).
Aplica a clientes.html, pagos.html e historial.html.
Uso: cd ~/inventario-qa/static && python3 qa_fix_cache_logo.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
archivos = ['clientes.html', 'pagos.html', 'historial.html']

viejo = '''function cargarImagenBase64(url){
  return new Promise(function(resolve, reject){
    fetch(url).then(function(r){ return r.blob(); }).then(function(blob){
      const reader = new FileReader();
      reader.onloadend = function(){ resolve(reader.result); };
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
        print("OK " + nombre + ": logo cacheado")
        total_ok += 1
    elif '_logoCacheDataUrl' in src:
        print("* " + nombre + ": ya estaba cacheado")
    else:
        print("ERROR " + nombre + ": no se encontro cargarImagenBase64 exacto")

print()
print("Total actualizado: " + str(total_ok) + " archivo(s)")
print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. Prueba de nuevo: la SEGUNDA vez que compartas un ticket")
print("(en cualquiera de las 3 paginas) deberia ser mas rapido y confiable.")
print("La primera vez despues de reiniciar el servicio puede seguir fallando")
print("(porque el cache esta vacio la primera vez), pero de ahi en adelante deberia ir bien.")
