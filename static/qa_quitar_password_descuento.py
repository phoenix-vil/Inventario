#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Quita la contraseña de autorizacion para el descuento general del
carrito -- cualquier cajero puede aplicarlo directamente, igual que ya
funciona el descuento por articulo individual.
Uso: cd ~/inventario-qa/static && python3 qa_quitar_password_descuento.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Simplificar el HTML del modal (quitar usuario/contrasena)
# ================================================================
viejo_html = '''<!-- Modal descuento extra (requiere autorización) -->
<div class="overlay" id="desc-modal">
  <div class="modal">
    <h2>Descuento extra</h2>
    <p style="font-size:13px;color:var(--text2);margin-bottom:12px" id="desc-info">Requiere autorización de un gerente.</p>
    <div class="field"><label>Porcentaje de descuento (%)</label><input type="number" id="d-pct" min="0" max="100" step="1" placeholder="0"></div>
    <div class="field"><label>Usuario gerente</label><input id="d-usuario" autocomplete="off"></div>
    <div class="field"><label>Contraseña</label><input type="password" id="d-password" autocomplete="off"></div>
    <div class="msg" id="desc-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarDescuento()">Cancelar</button>
      <button class="primary" onclick="autorizarDescuento()">Autorizar</button>
    </div>
  </div>
</div>'''

nuevo_html = '''<!-- Modal descuento extra -->
<div class="overlay" id="desc-modal">
  <div class="modal">
    <h2>Descuento extra</h2>
    <div class="field"><label>Porcentaje de descuento (%)</label><input type="number" id="d-pct" min="0" max="100" step="1" placeholder="0"></div>
    <div class="msg" id="desc-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarDescuento()">Cancelar</button>
      <button class="primary" onclick="autorizarDescuento()">Aplicar</button>
    </div>
  </div>
</div>'''

if viejo_html in src:
    src = src.replace(viejo_html, nuevo_html, 1)
    cambios.append('HTML del modal simplificado (sin usuario/contraseña)')
elif '<h2>Descuento extra</h2>\n    <div class="field"><label>Porcentaje' in src:
    cambios.append('* HTML ya estaba simplificado')
else:
    print("ERROR: no se encontro el HTML exacto del modal")

# ================================================================
# 2. Simplificar abrirDescuento()
# ================================================================
viejo_abrir = '''function abrirDescuento(){
  if(!carrito.length)return;
  document.getElementById('d-pct').value=descuentoExtra||'';
  const inputUsuario=document.getElementById('d-usuario');
  const info=document.getElementById('desc-info');
  if(sesionPOS && sesionPOS.rol==='gerente'){
    inputUsuario.value=sesionPOS.usuario;
    inputUsuario.readOnly=true;
    info.textContent=`El descuento debe autorizarse con tu propia sesión de gerente (${sesionPOS.usuario}).`;
  }else{
    inputUsuario.value='';
    inputUsuario.readOnly=false;
    info.textContent='Requiere autorización de un gerente.';
  }
  document.getElementById('d-password').value='';
  document.getElementById('desc-msg').className='msg';
  document.getElementById('desc-modal').classList.add('open');
}'''

nuevo_abrir = '''function abrirDescuento(){
  if(!carrito.length)return;
  document.getElementById('d-pct').value=descuentoExtra||'';
  document.getElementById('desc-msg').className='msg';
  document.getElementById('desc-modal').classList.add('open');
}'''

if viejo_abrir in src:
    src = src.replace(viejo_abrir, nuevo_abrir, 1)
    cambios.append('abrirDescuento() simplificada')
elif "function abrirDescuento(){\n  if(!carrito.length)return;\n  document.getElementById('d-pct').value=descuentoExtra||'';\n  document.getElementById('desc-msg')" in src:
    cambios.append('* abrirDescuento ya estaba simplificada')
else:
    print("ERROR: no se encontro abrirDescuento exacta")

# ================================================================
# 3. Simplificar autorizarDescuento() (sin llamada a /api/pos/autorizar)
# ================================================================
viejo_autorizar = '''async function autorizarDescuento(){
  const pct = parseFloat(document.getElementById('d-pct').value);
  const usuario = document.getElementById('d-usuario').value.trim();
  const password = document.getElementById('d-password').value;
  const msg = document.getElementById('desc-msg');
  if(isNaN(pct)||pct<0||pct>100){msg.className='msg error show';msg.textContent='Porcentaje inválido';return;}
  if(!usuario||!password){msg.className='msg error show';msg.textContent='Ingresa usuario y contraseña';return;}
  if(sesionPOS && sesionPOS.rol==='gerente' && usuario!==sesionPOS.usuario){
    msg.className='msg error show';
    msg.textContent=`El descuento debe ser autorizado por el gerente con la sesión activa (${sesionPOS.usuario}), no por otro usuario.`;
    return;
  }
  try{
    const r = await authFetch('/api/pos/autorizar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usuario,password,descuento_pct:pct})}, true);
    if(!r.ok){const e=await r.json();msg.className='msg error show';msg.textContent=e.detail||'No autorizado';return;}
    descuentoExtra=pct;autorizadoPor=usuario;
    actualizarTotales();
    cerrarDescuento();
  }catch(e){msg.className='msg error show';msg.textContent='Error de conexión';}
}'''

nuevo_autorizar = '''function autorizarDescuento(){
  const pct = parseFloat(document.getElementById('d-pct').value);
  const msg = document.getElementById('desc-msg');
  if(isNaN(pct)||pct<0||pct>100){msg.className='msg error show';msg.textContent='Porcentaje inválido';return;}
  descuentoExtra=pct;
  autorizadoPor=sesionPOS?sesionPOS.usuario:null;
  actualizarTotales();
  cerrarDescuento();
}'''

if viejo_autorizar in src:
    src = src.replace(viejo_autorizar, nuevo_autorizar, 1)
    cambios.append('autorizarDescuento() simplificada (sin contraseña)')
elif "function autorizarDescuento(){\n  const pct = parseFloat(document.getElementById('d-pct').value);\n  const msg = document.getElementById('desc-msg');" in src:
    cambios.append('* autorizarDescuento ya estaba simplificada')
else:
    print("ERROR: no se encontro autorizarDescuento exacta")

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
    print("Listo. Ahora cualquier cajero puede aplicar el descuento general")
    print("del carrito con solo el porcentaje, sin pedir contraseña.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
