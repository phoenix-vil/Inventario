#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega "Transferencia" como metodo de pago:
- database.py: nueva columna transferencia_referencia
- schemas.py: nuevo campo en RegistrarVenta
- main.py: logica de registro (pago_con=total, cambio=0, guarda referencia)
- pagos.html: boton, seccion, setMetodo(), confirmarCobro(), ticket
- historial.html: mismo bloque de ticket
Tambien de paso corrige un bug existente: el bloque de metodo de pago en
el ticket usaba if/if/else en vez de if/else-if/else, causando que una
venta a credito mostrara "A CREDITO" Y "EFECTIVO" a la vez.
Uso: cd ~/inventario-qa && python3 static/qa_agregar_transferencia.py
"""
import os, re

QA = os.path.expanduser('~/inventario-qa')

# ================================================================
# 1. database.py: nueva columna
# ================================================================
ruta_db = os.path.join(QA, 'database.py')
src = open(ruta_db, encoding='utf-8').read()
viejo = '    tpv_terminal = Column(String, nullable=True)\n    detalle_json = Column(String, nullable=False)'
nuevo = '    tpv_terminal = Column(String, nullable=True)\n    transferencia_referencia = Column(String, nullable=True)\n    detalle_json = Column(String, nullable=False)'
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta_db, 'w', encoding='utf-8').write(src)
    print("OK database.py: columna transferencia_referencia agregada")
elif 'transferencia_referencia' in src:
    print("* database.py: ya tenia la columna")
else:
    print("ERROR database.py: no se encontro el bloque exacto")

# ================================================================
# 2. schemas.py: nuevo campo
# ================================================================
ruta_schemas = os.path.join(QA, 'schemas.py')
src = open(ruta_schemas, encoding='utf-8').read()
viejo = '    tpv_terminal: Optional[str] = None\n    cliente_id: Optional[int] = None'
nuevo = '    tpv_terminal: Optional[str] = None\n    transferencia_referencia: Optional[str] = None\n    cliente_id: Optional[int] = None'
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    open(ruta_schemas, 'w', encoding='utf-8').write(src)
    print("OK schemas.py: campo transferencia_referencia agregado")
elif 'transferencia_referencia' in src:
    print("* schemas.py: ya tenia el campo")
else:
    print("ERROR schemas.py: no se encontro el bloque exacto")

# ================================================================
# 3. main.py: logica de registro
# ================================================================
ruta_main = os.path.join(QA, 'main.py')
src = open(ruta_main, encoding='utf-8').read()
cambios_main = []

viejo1 = 'metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "credito") else "efectivo"'
nuevo1 = 'metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia") else "efectivo"'
if viejo1 in src:
    src = src.replace(viejo1, nuevo1, 1)
    cambios_main.append('metodos validos actualizados')
elif '"transferencia"' in src:
    cambios_main.append('* metodos validos ya incluian transferencia')

viejo2 = '''    if metodo == "tarjeta":
        # En tarjeta no hay cambio; el pago es por el total exacto
        pago_con = total
        cambio = 0.0
    elif metodo == "credito":'''
nuevo2 = '''    if metodo == "tarjeta" or metodo == "transferencia":
        # En tarjeta/transferencia no hay cambio; el pago es por el total exacto
        pago_con = total
        cambio = 0.0
    elif metodo == "credito":'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    cambios_main.append('logica de pago_con/cambio actualizada')
elif 'metodo == "tarjeta" or metodo == "transferencia"' in src:
    cambios_main.append('* logica de pago_con ya incluia transferencia')

viejo3 = '''        tpv_terminal=data.tpv_terminal if metodo == "tarjeta" else None,
        detalle_json=json.dumps(detalle, ensure_ascii=False),'''
nuevo3 = '''        tpv_terminal=data.tpv_terminal if metodo == "tarjeta" else None,
        transferencia_referencia=data.transferencia_referencia if metodo == "transferencia" else None,
        detalle_json=json.dumps(detalle, ensure_ascii=False),'''
if viejo3 in src:
    src = src.replace(viejo3, nuevo3, 1)
    cambios_main.append('guardado de transferencia_referencia agregado')
elif 'transferencia_referencia=data.transferencia_referencia' in src:
    cambios_main.append('* guardado ya incluia transferencia_referencia')

viejo4 = '''        "tpv_terminal": venta.tpv_terminal,
        "autorizado_por": data.autorizado_por,'''
nuevo4 = '''        "tpv_terminal": venta.tpv_terminal,
        "transferencia_referencia": venta.transferencia_referencia,
        "autorizado_por": data.autorizado_por,'''
if viejo4 in src:
    src = src.replace(viejo4, nuevo4, 1)
    cambios_main.append('respuesta incluye transferencia_referencia')
elif '"transferencia_referencia": venta.transferencia_referencia' in src:
    cambios_main.append('* respuesta ya incluia transferencia_referencia')

if cambios_main:
    open(ruta_main, 'w', encoding='utf-8').write(src)
for c in cambios_main:
    print("OK main.py: " + c)
if not cambios_main:
    print("ERROR main.py: no se aplico ningun cambio, revisar")

# ================================================================
# 4. pagos.html: boton + seccion + setMetodo + confirmarCobro + ticket
# ================================================================
ruta_pagos = os.path.join(QA, 'static', 'pagos.html')
src = open(ruta_pagos, encoding='utf-8').read()
cambios_pagos = []

# 4a. Boton
viejo = '''        <button type="button" id="btn-credito" class="metodo-btn" onclick="setMetodo('credito')">📒 Crédito</button>
      </div>'''
nuevo = '''        <button type="button" id="btn-credito" class="metodo-btn" onclick="setMetodo('credito')">📒 Crédito</button>
        <button type="button" id="btn-transferencia" class="metodo-btn" onclick="setMetodo('transferencia')">🏦 Transferencia</button>
      </div>'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    cambios_pagos.append('boton agregado')
elif 'btn-transferencia' in src:
    cambios_pagos.append('* boton ya existia')

# 4b. Seccion (despues de sec-tarjeta, antes de sec-credito)
viejo = '''    <!-- Sección crédito (buscar o crear cliente) -->
    <div id="sec-credito" style="display:none">'''
nuevo = '''    <!-- Sección transferencia -->
    <div id="sec-transferencia" style="display:none">
      <div class="field"><label>Referencia / Folio (opcional)</label><input id="c-transf-ref" placeholder="Ej: 998877" autocomplete="off"></div>
    </div>
    <!-- Sección crédito (buscar o crear cliente) -->
    <div id="sec-credito" style="display:none">'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    cambios_pagos.append('seccion agregada')
elif 'sec-transferencia' in src:
    cambios_pagos.append('* seccion ya existia')

# 4c. setMetodo()
viejo = '''function setMetodo(m){
  metodoPago = m;
  document.getElementById('btn-efectivo').classList.toggle('activo', m==='efectivo');
  document.getElementById('btn-tarjeta').classList.toggle('activo', m==='tarjeta');
  document.getElementById('btn-credito').classList.toggle('activo', m==='credito');
  document.getElementById('sec-efectivo').style.display = m==='efectivo'?'block':'none';
  document.getElementById('sec-tarjeta').style.display = m==='tarjeta'?'block':'none';
  document.getElementById('sec-credito').style.display = m==='credito'?'block':'none';
  document.getElementById('cobro-msg').className='msg';
}'''
nuevo = '''function setMetodo(m){
  metodoPago = m;
  document.getElementById('btn-efectivo').classList.toggle('activo', m==='efectivo');
  document.getElementById('btn-tarjeta').classList.toggle('activo', m==='tarjeta');
  document.getElementById('btn-credito').classList.toggle('activo', m==='credito');
  document.getElementById('btn-transferencia').classList.toggle('activo', m==='transferencia');
  document.getElementById('sec-efectivo').style.display = m==='efectivo'?'block':'none';
  document.getElementById('sec-tarjeta').style.display = m==='tarjeta'?'block':'none';
  document.getElementById('sec-credito').style.display = m==='credito'?'block':'none';
  document.getElementById('sec-transferencia').style.display = m==='transferencia'?'block':'none';
  document.getElementById('cobro-msg').className='msg';
}'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    cambios_pagos.append('setMetodo() actualizada')
elif "btn-transferencia').classList.toggle" in src:
    cambios_pagos.append('* setMetodo ya estaba actualizada')

# 4d. confirmarCobro()
viejo = '''  }else if(metodoPago==='credito'){
    if(!clienteSeleccionado){
      msg.className='msg error show';msg.textContent='Selecciona o crea un cliente para la venta a crédito';return;
    }
    body.cliente_id=clienteSeleccionado.id;
  }'''
nuevo = '''  }else if(metodoPago==='credito'){
    if(!clienteSeleccionado){
      msg.className='msg error show';msg.textContent='Selecciona o crea un cliente para la venta a crédito';return;
    }
    body.cliente_id=clienteSeleccionado.id;
  }else if(metodoPago==='transferencia'){
    body.transferencia_referencia=document.getElementById('c-transf-ref').value.trim()||null;
  }'''
if viejo in src:
    src = src.replace(viejo, nuevo, 1)
    cambios_pagos.append('confirmarCobro() actualizada')
elif 'transferencia_referencia=document.getElementById' in src:
    cambios_pagos.append('* confirmarCobro ya estaba actualizada')

# 4e. Ticket: corregir if/if/else -> if/elseif/elseif/else y agregar transferencia
viejo = '''  if(v.metodo_pago==='credito'){
    html+=`<div class="tk-line" style="color:var(--amber)"><span>Pago</span><span>A CRÉDITO</span></div>`;
    if(v.cliente_nombre)html+=`<div class="tk-line"><span>Cliente</span><span>${esc(v.cliente_nombre)}</span></div>`;
  }
  if(v.metodo_pago==='tarjeta'){
    html+=`<div class="tk-line"><span>Pago</span><span>TARJETA</span></div>`;
    if(v.tpv_terminal)html+=`<div class="tk-line"><span>Terminal</span><span>${esc(v.tpv_terminal)}</span></div>`;
    if(v.tpv_referencia)html+=`<div class="tk-line"><span>Referencia</span><span>${esc(v.tpv_referencia)}</span></div>`;
    if(v.tpv_autorizacion)html+=`<div class="tk-line"><span>Autorización</span><span>${esc(v.tpv_autorizacion)}</span></div>`;
  }else{
    html+=`<div class="tk-line"><span>Pago</span><span>EFECTIVO</span></div>`;
    if(v.pago_con!=null){
      html+=`<div class="tk-line"><span>Pagó con</span><span>${money(v.pago_con)}</span></div>`;
      html+=`<div class="tk-line"><span>Cambio</span><span>${money(v.cambio||0)}</span></div>`;
    }
  }'''
nuevo = '''  if(v.metodo_pago==='credito'){
    html+=`<div class="tk-line" style="color:var(--amber)"><span>Pago</span><span>A CRÉDITO</span></div>`;
    if(v.cliente_nombre)html+=`<div class="tk-line"><span>Cliente</span><span>${esc(v.cliente_nombre)}</span></div>`;
  }else if(v.metodo_pago==='tarjeta'){
    html+=`<div class="tk-line"><span>Pago</span><span>TARJETA</span></div>`;
    if(v.tpv_terminal)html+=`<div class="tk-line"><span>Terminal</span><span>${esc(v.tpv_terminal)}</span></div>`;
    if(v.tpv_referencia)html+=`<div class="tk-line"><span>Referencia</span><span>${esc(v.tpv_referencia)}</span></div>`;
    if(v.tpv_autorizacion)html+=`<div class="tk-line"><span>Autorización</span><span>${esc(v.tpv_autorizacion)}</span></div>`;
  }else if(v.metodo_pago==='transferencia'){
    html+=`<div class="tk-line"><span>Pago</span><span>TRANSFERENCIA</span></div>`;
    if(v.transferencia_referencia)html+=`<div class="tk-line"><span>Referencia</span><span>${esc(v.transferencia_referencia)}</span></div>`;
  }else{
    html+=`<div class="tk-line"><span>Pago</span><span>EFECTIVO</span></div>`;
    if(v.pago_con!=null){
      html+=`<div class="tk-line"><span>Pagó con</span><span>${money(v.pago_con)}</span></div>`;
      html+=`<div class="tk-line"><span>Cambio</span><span>${money(v.cambio||0)}</span></div>`;
    }
  }'''
n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    cambios_pagos.append('ticket (generarTicketHTML) actualizado y bug if/if/else corregido')
elif "'TRANSFERENCIA'" in src:
    cambios_pagos.append('* ticket ya estaba actualizado')
else:
    print("ERROR pagos.html: no se encontro el bloque de ticket exacto (coincidencias: " + str(n) + ")")

if cambios_pagos:
    open(ruta_pagos, 'w', encoding='utf-8').write(src)
for c in cambios_pagos:
    print("OK pagos.html: " + c)

# ================================================================
# 5. historial.html: mismo bloque de ticket (ticketHTML)
# ================================================================
ruta_hist = os.path.join(QA, 'static', 'historial.html')
src = open(ruta_hist, encoding='utf-8').read()
n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    open(ruta_hist, 'w', encoding='utf-8').write(src)
    print("OK historial.html: ticket (ticketHTML) actualizado")
elif "'TRANSFERENCIA'" in src:
    print("* historial.html: ticket ya estaba actualizado")
else:
    print("ERROR historial.html: no se encontro el bloque de ticket exacto (coincidencias: " + str(n) + ")")

# ================================================================
# Verificar
# ================================================================
print()
ok_total = True
for ruta_check in [ruta_pagos, ruta_hist]:
    s = open(ruta_check, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + os.path.basename(ruta_check) + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 55)
if ok_total:
    print("Archivos guardados. AHORA FALTA:")
    print("1. Migrar la base de datos (agregar la columna nueva):")
    print("   sqlite3 ~/inventario-qa/inventario.db \"ALTER TABLE ventas ADD COLUMN transferencia_referencia TEXT;\"")
    print("2. Reiniciar el servicio:")
    print("   sudo systemctl restart inventario-qa")
else:
    print("ADVERTENCIA: desbalance de llaves en algun archivo HTML. Revisar antes de continuar.")
