#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Quita el bloque JS duplicado de pagos.html (confirmarPersonalizado/
promptPersonalizado locales), que ahora chocan con las mismas funciones
recien agregadas a auth.js. Tambien quita el modal HTML "prompt-generico-modal"
que estaba duplicado en pagos.html, ya que auth.js lo inyecta solo.
Uso: cd ~/inventario-qa/static && python3 qa_fix_colision_modales.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Quitar el bloque JS duplicado (variables + 3 funciones)
# ================================================================
viejo_js = '''let _resolverConfirmarGenerico = null;
let _resolverPromptFn = null;
function promptPersonalizado(mensaje, valorDefault, titulo){
  return new Promise((resolve)=>{
    document.getElementById('prompt-generico-titulo').textContent = titulo || 'Escribe un valor';
    document.getElementById('prompt-generico-mensaje').textContent = mensaje || '';
    const input = document.getElementById('prompt-generico-input');
    input.value = valorDefault || '';
    document.getElementById('prompt-generico-modal').classList.add('open');
    setTimeout(()=>input.focus(), 60);
    _resolverPromptFn = (valor)=>{
      document.getElementById('prompt-generico-modal').classList.remove('open');
      _resolverPromptFn = null;
      resolve(valor);
    };
  });
}
function _cancelarPromptGenerico(){
  if(_resolverPromptFn) _resolverPromptFn(null);
}
function _aceptarPromptGenerico(){
  const valor = document.getElementById('prompt-generico-input').value;
  if(_resolverPromptFn) _resolverPromptFn(valor);
}
function confirmarPersonalizado(mensaje, titulo){
  return new Promise((resolve)=>{
    document.getElementById('confirmar-generico-titulo').textContent = titulo || '¿Confirmar?';
    document.getElementById('confirmar-generico-mensaje').textContent = mensaje;
    document.getElementById('modal-confirmar-generico').classList.add('open');
    _resolverConfirmarGenerico = (valor)=>{
      document.getElementById('modal-confirmar-generico').classList.remove('open');
      _resolverConfirmarGenerico = null;
      resolve(valor);
    };
  });
}'''

n1 = src.count(viejo_js)
if n1 == 1:
    src = src.replace(viejo_js, '', 1)
    cambios.append('bloque JS duplicado eliminado de pagos.html')
else:
    print("ERROR: no se encontro el bloque JS exacto (coincidencias: " + str(n1) + ")")

# ================================================================
# 2. Quitar el modal HTML "prompt-generico-modal" duplicado
# ================================================================
patron_modal = re.compile(
    r'<!-- Modal de prompt generico \(reemplaza prompt\(\) nativo\) -->\s*'
    r'<div class="overlay" id="prompt-generico-modal">.*?</div>\s*</div>\s*</div>\s*',
    re.DOTALL
)
m = patron_modal.search(src)
if m:
    src = patron_modal.sub('', src, count=1)
    cambios.append('modal HTML duplicado "prompt-generico-modal" eliminado')
else:
    print("* No se encontro el modal HTML duplicado con ese patron (puede que ya se haya quitado)")

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
    print("Listo. Punto de Venta ya no deberia tener el error de sintaxis.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
