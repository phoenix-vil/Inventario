#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige la logica JS del descuento general que quedo desactualizada
(seguia buscando el campo d-pct que ya no existe tras el cambio de HTML).
Usa el contenido exacto confirmado con grep.
Uso: cd ~/inventario-qa/static && python3 qa_fix_js_descuento_general.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()

viejo = '''function abrirDescuento(){
  if(!carrito.length)return;
  document.getElementById('d-pct').value=descuentoExtra||'';
  document.getElementById('desc-msg').className='msg';
  document.getElementById('desc-modal').classList.add('open');
}
function cerrarDescuento(){document.getElementById('desc-modal').classList.remove('open');}

function autorizarDescuento(){
  const pct = parseFloat(document.getElementById('d-pct').value);
  const msg = document.getElementById('desc-msg');
  if(isNaN(pct)||pct<0||pct>100){msg.className='msg error show';msg.textContent='Porcentaje inválido';return;}
  descuentoExtra=pct;
  autorizadoPor=sesionPOS?sesionPOS.usuario:null;
  actualizarTotales();
  cerrarDescuento();
}'''

nuevo = '''let modoDescGeneral = 'pct';
function setModoDescGeneral(modo){
  modoDescGeneral = modo;
  document.getElementById('desc-modo-pct').classList.toggle('activo', modo==='pct');
  document.getElementById('desc-modo-monto').classList.toggle('activo', modo==='monto');
  document.getElementById('d-valor').placeholder = modo==='pct' ? '0' : '0.00';
}
function abrirDescuento(){
  if(!carrito.length)return;
  setModoDescGeneral('pct');
  document.getElementById('d-valor').value=descuentoExtra||'';
  document.getElementById('desc-msg').className='msg';
  document.getElementById('desc-modal').classList.add('open');
}
function cerrarDescuento(){document.getElementById('desc-modal').classList.remove('open');}

function autorizarDescuento(){
  const valor = parseFloat(document.getElementById('d-valor').value);
  const msg = document.getElementById('desc-msg');
  if(isNaN(valor)||valor<0){msg.className='msg error show';msg.textContent='Valor inválido';return;}
  let pct;
  if(modoDescGeneral==='monto'){
    const subtotal = calcSubtotal();
    if(subtotal<=0){msg.className='msg error show';msg.textContent='El carrito está vacío';return;}
    if(valor>subtotal){msg.className='msg error show';msg.textContent='El monto no puede ser mayor al subtotal';return;}
    pct = Math.round((valor/subtotal)*10000)/100;
  }else{
    if(valor>100){msg.className='msg error show';msg.textContent='El porcentaje no puede ser mayor a 100';return;}
    pct = valor;
  }
  descuentoExtra=pct;
  autorizadoPor=sesionPOS?sesionPOS.usuario:null;
  actualizarTotales();
  cerrarDescuento();
}'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("OK: logica del descuento general corregida (soporta %/$)")
elif 'modoDescGeneral' in src:
    print("* Ya estaba corregida")
else:
    print("ERROR: no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Prueba el descuento general en QA (ambos modos: % y $).")
    print()
    print("Cuando confirmes que funciona, copia SOLO pagos.html a produccion:")
    print("  cp ~/inventario-qa/static/pagos.html ~/inventario/static/pagos.html")
    print("  sudo systemctl restart inventario")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
