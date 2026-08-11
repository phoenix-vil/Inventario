#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega "Credito" como forma de pago en pagos.html: boton + seccion con
buscador/creador de cliente.
Corre DESPUES de creditos_backend.py
Uso: cd ~/inventario/static && python3 creditos_pagos_frontend.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Boton "Credito" junto a Efectivo/Tarjeta
# ================================================================
viejo_botones = '''        <button type="button" id="btn-efectivo" class="metodo-btn activo" onclick="setMetodo('efectivo')">💵 Efectivo</button>
        <button type="button" id="btn-tarjeta" class="metodo-btn" onclick="setMetodo('tarjeta')">💳 Tarjeta</button>'''

nuevo_botones = '''        <button type="button" id="btn-efectivo" class="metodo-btn activo" onclick="setMetodo('efectivo')">💵 Efectivo</button>
        <button type="button" id="btn-tarjeta" class="metodo-btn" onclick="setMetodo('tarjeta')">💳 Tarjeta</button>
        <button type="button" id="btn-credito" class="metodo-btn" onclick="setMetodo('credito')">📒 Crédito</button>'''

if src.count(viejo_botones) == 1:
    src = src.replace(viejo_botones, nuevo_botones, 1)
    cambios.append('Boton Credito agregado')
else:
    print("ADVERTENCIA: no se encontro el bloque de botones de metodo de pago")

# ================================================================
# 2. Seccion "sec-credito" (buscador/creador de cliente)
# ================================================================
viejo_seccion = '''    <!-- Sección tarjeta (datos del ticket de la TPV) -->
    <div id="sec-tarjeta" style="display:none">
      <div class="field"><label>Terminal (TPV)</label><input id="c-tpv-term" placeholder="Ej: Clip, BBVA, etc." autocomplete="off"></div>
      <div class="field"><label>Referencia / No. de operación *</label><input id="c-tpv-ref" placeholder="Ej: 001234" autocomplete="off"></div>
      <div class="field"><label>Código de autorización *</label><input id="c-tpv-aut" placeholder="Ej: 456789" autocomplete="off"></div>
    </div>'''

nuevo_seccion = '''    <!-- Sección tarjeta (datos del ticket de la TPV) -->
    <div id="sec-tarjeta" style="display:none">
      <div class="field"><label>Terminal (TPV)</label><input id="c-tpv-term" placeholder="Ej: Clip, BBVA, etc." autocomplete="off"></div>
      <div class="field"><label>Referencia / No. de operación *</label><input id="c-tpv-ref" placeholder="Ej: 001234" autocomplete="off"></div>
      <div class="field"><label>Código de autorización *</label><input id="c-tpv-aut" placeholder="Ej: 456789" autocomplete="off"></div>
    </div>
    <!-- Sección crédito (buscar o crear cliente) -->
    <div id="sec-credito" style="display:none">
      <div class="field">
        <label>Cliente *</label>
        <input type="text" id="c-cliente-buscar" placeholder="Buscar cliente por nombre..." autocomplete="off" oninput="buscarClienteCredito()">
        <div id="c-cliente-resultados" style="margin-top:6px"></div>
        <div id="c-cliente-seleccionado" style="display:none;margin-top:8px;padding:.625rem .875rem;background:var(--blue-bg);border-radius:8px;font-size:13px;color:var(--blue);font-weight:600"></div>
      </div>
      <button type="button" onclick="mostrarNuevoCliente()" style="background:none;border:none;color:var(--blue);font-size:13px;cursor:pointer;padding:4px 0;text-decoration:underline">+ Crear cliente nuevo</button>
      <div id="c-cliente-nuevo" style="display:none;margin-top:8px;padding:.875rem;background:var(--bg);border-radius:10px">
        <div class="field"><label>Nombre *</label><input type="text" id="c-nuevo-nombre" placeholder="Nombre del cliente"></div>
        <div class="field"><label>Teléfono (opcional)</label><input type="text" id="c-nuevo-telefono" placeholder="10 dígitos"></div>
        <button type="button" onclick="crearClienteRapido()" style="width:100%;height:40px;border:none;border-radius:8px;background:var(--blue);color:#fff;font-weight:600;cursor:pointer">Crear y seleccionar</button>
      </div>
    </div>'''

if src.count(viejo_seccion) == 1:
    src = src.replace(viejo_seccion, nuevo_seccion, 1)
    cambios.append('Seccion sec-credito agregada')
else:
    print("ADVERTENCIA: no se encontro el bloque de la seccion tarjeta")

# ================================================================
# 3. setMetodo(): agregar el toggle de credito
# ================================================================
viejo_setmetodo = '''function setMetodo(m){
  metodoPago = m;
  document.getElementById('btn-efectivo').classList.toggle('activo', m==='efectivo');
  document.getElementById('btn-tarjeta').classList.toggle('activo', m==='tarjeta');
  document.getElementById('sec-efectivo').style.display = m==='efectivo'?'block':'none';
  document.getElementById('sec-tarjeta').style.display = m==='tarjeta'?'block':'none';
  document.getElementById('cobro-msg').className='msg';
}'''

nuevo_setmetodo = '''function setMetodo(m){
  metodoPago = m;
  document.getElementById('btn-efectivo').classList.toggle('activo', m==='efectivo');
  document.getElementById('btn-tarjeta').classList.toggle('activo', m==='tarjeta');
  document.getElementById('btn-credito').classList.toggle('activo', m==='credito');
  document.getElementById('sec-efectivo').style.display = m==='efectivo'?'block':'none';
  document.getElementById('sec-tarjeta').style.display = m==='tarjeta'?'block':'none';
  document.getElementById('sec-credito').style.display = m==='credito'?'block':'none';
  document.getElementById('cobro-msg').className='msg';
}

let clienteSeleccionado = null;

async function buscarClienteCredito(){
  const q = document.getElementById('c-cliente-buscar').value.trim();
  const cont = document.getElementById('c-cliente-resultados');
  if(!q){ cont.innerHTML=''; return; }
  try{
    const r = await authFetch('/api/clientes?q='+encodeURIComponent(q));
    const clientes = await r.json();
    if(!clientes.length){ cont.innerHTML='<div style="font-size:12px;color:var(--text2);padding:6px 0">Sin resultados</div>'; return; }
    cont.innerHTML = clientes.slice(0,6).map(c=>{
      const saldoTxt = c.saldo>0 ? ` · debe ${money(c.saldo)}` : '';
      return `<div onclick='seleccionarCliente(${c.id},"${esc(c.nombre).replace(/"/g,'&quot;')}",${c.saldo})' style="padding:8px 10px;border:0.5px solid var(--border);border-radius:8px;margin-bottom:4px;cursor:pointer;font-size:13px">
        <strong>${esc(c.nombre)}</strong>${saldoTxt}
      </div>`;
    }).join('');
  }catch(e){}
}

function seleccionarCliente(id, nombre, saldo){
  clienteSeleccionado = {id, nombre};
  document.getElementById('c-cliente-buscar').value='';
  document.getElementById('c-cliente-resultados').innerHTML='';
  const sel = document.getElementById('c-cliente-seleccionado');
  sel.style.display='block';
  const saldoTxt = saldo>0 ? ` (debe actualmente ${money(saldo)})` : '';
  sel.textContent = '👤 ' + nombre + saldoTxt;
}

function mostrarNuevoCliente(){
  document.getElementById('c-cliente-nuevo').style.display='block';
  document.getElementById('c-nuevo-nombre').focus();
}

async function crearClienteRapido(){
  const nombre = document.getElementById('c-nuevo-nombre').value.trim();
  if(!nombre){ alert('Escribe el nombre del cliente'); return; }
  const telefono = document.getElementById('c-nuevo-telefono').value.trim() || null;
  try{
    const r = await authFetch('/api/clientes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nombre, telefono})
    });
    const data = await r.json();
    if(!r.ok){ alert(data.detail||'No se pudo crear el cliente'); return; }
    seleccionarCliente(data.id, data.nombre, 0);
    document.getElementById('c-cliente-nuevo').style.display='none';
    document.getElementById('c-nuevo-nombre').value='';
    document.getElementById('c-nuevo-telefono').value='';
  }catch(e){ alert('Error de conexión'); }
}'''

n_sm = src.count(viejo_setmetodo)
if n_sm == 1:
    src = src.replace(viejo_setmetodo, nuevo_setmetodo, 1)
    cambios.append('setMetodo() y funciones de cliente agregadas')
else:
    print("ADVERTENCIA: no se encontro setMetodo() exacto (coincidencias: " + str(n_sm) + ")")

# ================================================================
# 4. abrirCobro(): resetear la seccion de cliente al abrir
# ================================================================
viejo_abrir = '''  document.getElementById('c-tpv-term').value='';
  document.getElementById('cobro-msg').className='msg';
  setMetodo('efectivo');'''

nuevo_abrir = '''  document.getElementById('c-tpv-term').value='';
  document.getElementById('c-cliente-buscar').value='';
  document.getElementById('c-cliente-resultados').innerHTML='';
  document.getElementById('c-cliente-seleccionado').style.display='none';
  document.getElementById('c-cliente-nuevo').style.display='none';
  clienteSeleccionado = null;
  document.getElementById('cobro-msg').className='msg';
  setMetodo('efectivo');'''

n_ac = src.count(viejo_abrir)
if n_ac == 1:
    src = src.replace(viejo_abrir, nuevo_abrir, 1)
    cambios.append('abrirCobro() resetea la seleccion de cliente')
else:
    print("ADVERTENCIA: no se encontro el bloque exacto de abrirCobro (coincidencias: " + str(n_ac) + ")")

# ================================================================
# 5. confirmarCobro(): validar cliente y mandar cliente_id
# ================================================================
viejo_confirmar = '''  }else{
    // Tarjeta: pedir datos del ticket de la TPV
    const ref=document.getElementById('c-tpv-ref').value.trim();
    const aut=document.getElementById('c-tpv-aut').value.trim();
    if(!ref||!aut){
      msg.className='msg error show';msg.textContent='Ingresa la referencia y autorización de la TPV';return;
    }
    body.tpv_referencia=ref;
    body.tpv_autorizacion=aut;
    body.tpv_terminal=document.getElementById('c-tpv-term').value.trim()||null;
  }'''

nuevo_confirmar = '''  }else if(metodoPago==='tarjeta'){
    // Tarjeta: pedir datos del ticket de la TPV
    const ref=document.getElementById('c-tpv-ref').value.trim();
    const aut=document.getElementById('c-tpv-aut').value.trim();
    if(!ref||!aut){
      msg.className='msg error show';msg.textContent='Ingresa la referencia y autorización de la TPV';return;
    }
    body.tpv_referencia=ref;
    body.tpv_autorizacion=aut;
    body.tpv_terminal=document.getElementById('c-tpv-term').value.trim()||null;
  }else if(metodoPago==='credito'){
    if(!clienteSeleccionado){
      msg.className='msg error show';msg.textContent='Selecciona o crea un cliente para la venta a crédito';return;
    }
    body.cliente_id=clienteSeleccionado.id;
  }'''

n_cc = src.count(viejo_confirmar)
if n_cc == 1:
    src = src.replace(viejo_confirmar, nuevo_confirmar, 1)
    cambios.append('confirmarCobro() valida cliente y envia cliente_id')
else:
    print("ADVERTENCIA: no se encontro el bloque exacto de confirmarCobro (coincidencias: " + str(n_cc) + ")")

# ================================================================
# 6. Ticket: mostrar "A credito - Cliente: X" si aplica
# ================================================================
viejo_ticket_metodo = '''  if(v.metodo_pago==='tarjeta'){
    html+=`<div class="tk-line"><span>Pago</span><span>TARJETA</span></div>`;'''

nuevo_ticket_metodo = '''  if(v.metodo_pago==='credito'){
    html+=`<div class="tk-line" style="color:var(--amber)"><span>Pago</span><span>A CRÉDITO</span></div>`;
    if(v.cliente_nombre)html+=`<div class="tk-line"><span>Cliente</span><span>${esc(v.cliente_nombre)}</span></div>`;
  }
  if(v.metodo_pago==='tarjeta'){
    html+=`<div class="tk-line"><span>Pago</span><span>TARJETA</span></div>`;'''

n_tk = src.count(viejo_ticket_metodo)
if n_tk == 1:
    src = src.replace(viejo_ticket_metodo, nuevo_ticket_metodo, 1)
    cambios.append('Ticket muestra "A CRÉDITO" y el nombre del cliente')
else:
    print("ADVERTENCIA: no se encontro el bloque exacto del ticket (coincidencias: " + str(n_tk) + ")")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print()
    print("Cambios aplicados:")
    for c in cambios:
        print("  OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Ya puedes cobrar 'A crédito' en Punto de venta.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
    print("Revisa static/pagos.html manualmente.")
