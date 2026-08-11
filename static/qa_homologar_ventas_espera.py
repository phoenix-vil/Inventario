#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Homologa las ventanas nativas del navegador en el flujo de ventas
en espera:
- borrarPendiente(): usa el modal de confirmacion ya existente
- dejarEnEspera(): usa un nuevo modal tipo "prompt" con campo de texto
Uso: cd ~/inventario-qa/static && python3 qa_homologar_ventas_espera.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Agregar el modal de "prompt" generico (antes de </body>)
# ================================================================
if 'id="prompt-generico-modal"' not in src:
    modal_html = '''
<!-- Modal de prompt generico (reemplaza prompt() nativo) -->
<div class="overlay" id="prompt-generico-modal">
  <div class="modal">
    <h2 id="prompt-generico-titulo">Escribe un valor</h2>
    <p id="prompt-generico-mensaje" style="font-size:13px;color:var(--text2);margin-bottom:12px"></p>
    <div class="field"><input type="text" id="prompt-generico-input" autocomplete="off"></div>
    <div class="modal-footer">
      <button onclick="_cancelarPromptGenerico()">Cancelar</button>
      <button class="primary" onclick="_aceptarPromptGenerico()">Aceptar</button>
    </div>
  </div>
</div>
'''
    if '</body>' in src:
        src = src.replace('</body>', modal_html + '\n</body>', 1)
        cambios.append('modal de prompt generico agregado')
    else:
        print("ERROR: no se encontro </body>")
else:
    cambios.append('* modal de prompt ya existia')

# ================================================================
# 2. Agregar la funcion promptPersonalizado() (junto a confirmarPersonalizado)
# ================================================================
if 'function promptPersonalizado' not in src:
    funcion_prompt = '''
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

'''
    marcador = 'function confirmarPersonalizado(mensaje, titulo){'
    if marcador in src:
        src = src.replace(marcador, funcion_prompt + marcador, 1)
        cambios.append('funcion promptPersonalizado() agregada')
    else:
        print("ERROR: no se encontro 'function confirmarPersonalizado(mensaje, titulo){'")
else:
    cambios.append('* promptPersonalizado ya existia')

# ================================================================
# 3. Actualizar dejarEnEspera() para usar el nuevo prompt
# ================================================================
viejo_dejar = '''  if(!carrito.length){ alert('El carrito está vacío'); return; }
  const nota = prompt('Nota para identificar esta venta (opcional):', '');
  if(nota===null) return;'''

nuevo_dejar = '''  if(!carrito.length){ alert('El carrito está vacío'); return; }
  const nota = await promptPersonalizado('Nota para identificar esta venta (opcional):', '', 'Dejar en espera');
  if(nota===null) return;'''

if viejo_dejar in src:
    src = src.replace(viejo_dejar, nuevo_dejar, 1)
    cambios.append('dejarEnEspera() usa el modal de prompt')
elif 'promptPersonalizado(\'Nota para identificar' in src:
    cambios.append('* dejarEnEspera ya usaba el modal')
else:
    print("ERROR: no se encontro el bloque exacto de dejarEnEspera")

# ================================================================
# 4. Actualizar borrarPendiente() para usar el modal de confirmacion
# ================================================================
viejo_borrar = '''async function borrarPendiente(id){
  if(!confirm('¿Eliminar esta venta en espera? No se puede deshacer.')) return;'''

nuevo_borrar = '''async function borrarPendiente(id){
  const ok = await confirmarPersonalizado('¿Eliminar esta venta en espera? No se puede deshacer.', 'Eliminar venta en espera');
  if(!ok) return;'''

if viejo_borrar in src:
    src = src.replace(viejo_borrar, nuevo_borrar, 1)
    cambios.append('borrarPendiente() usa el modal de confirmacion')
elif "confirmarPersonalizado('¿Eliminar esta venta en espera?" in src:
    cambios.append('* borrarPendiente ya usaba el modal')
else:
    print("ERROR: no se encontro el bloque exacto de borrarPendiente")

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
    print("Listo. Dejar en espera y Eliminar venta en espera ahora usan")
    print("modales propios en vez de las ventanas nativas del navegador.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
