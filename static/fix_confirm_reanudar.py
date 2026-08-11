#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reemplaza el dialogo nativo confirm() en reanudarPendiente() por un modal
propio, ya que en iOS (modo pantalla de inicio) los dialogos nativos a
veces se bloquean silenciosamente sin mostrar nada.
Uso: cd ~/inventario/static && python3 fix_confirm_reanudar.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar el modal de confirmacion personalizado (HTML), antes de </body>
# ================================================================
if 'modal-confirmar-generico' not in src:
    modal_html = '''
<!-- Modal de confirmacion generico (reemplaza confirm() nativo, poco fiable en iOS standalone) -->
<div class="overlay" id="modal-confirmar-generico">
  <div class="modal">
    <h2 id="confirmar-generico-titulo">¿Confirmar?</h2>
    <p id="confirmar-generico-mensaje" style="font-size:14px;color:var(--text2);margin-bottom:1.25rem;white-space:pre-line"></p>
    <div class="modal-footer">
      <button onclick="_resolverConfirmarGenerico(false)">Cancelar</button>
      <button class="primary" onclick="_resolverConfirmarGenerico(true)">Continuar</button>
    </div>
  </div>
</div>
'''
    src = src.replace('</body>', modal_html + '\n</body>', 1)
    print("1. Modal de confirmacion agregado")
else:
    print("1. * El modal ya existia, se omite")

# ================================================================
# 2. Agregar la funcion confirmarPersonalizado() (basada en Promise)
# ================================================================
if 'function confirmarPersonalizado' not in src:
    funcion = '''
let _resolverConfirmarGenerico = null;
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
}

'''
    marcador = 'async function reanudarPendiente(id){'
    if marcador in src:
        src = src.replace(marcador, funcion + marcador, 1)
        print("2. Funcion confirmarPersonalizado() agregada")
    else:
        print("2. ERROR: no se encontro 'async function reanudarPendiente(id){'")
else:
    print("2. * La funcion ya existia, se omite")

# ================================================================
# 3. Usar confirmarPersonalizado() en reanudarPendiente() en vez de confirm()
# ================================================================
viejo = '''async function reanudarPendiente(id){
  if(carrito.length>0){
    const confirmar = confirm('Ya tienes productos en el carrito actual. Si continúas, se perderán. ¿Continuar de todas formas?');
    if(!confirmar) return;
  }'''

nuevo = '''async function reanudarPendiente(id){
  if(carrito.length>0){
    const confirmar = await confirmarPersonalizado('Ya tienes productos en el carrito actual. Si continúas, se perderán.', '⚠️ Carrito con productos');
    if(!confirmar) return;
  }'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("3. reanudarPendiente() ahora usa el modal propio")
elif 'await confirmarPersonalizado(' in src and "reanudarPendiente" in src:
    print("3. * Ya estaba usando el modal propio")
else:
    print("3. ERROR: no se encontro el bloque exacto de reanudarPendiente")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Prueba de nuevo: con productos en el carrito, da clic en Reanudar.")
    print("Deberia aparecer un cuadro de confirmacion con el diseno de la app (no el del navegador).")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
