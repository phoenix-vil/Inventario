#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega el boton de eliminar cliente (solo gerentes) en el modal de detalle.
El backend ya bloquea el borrado si el cliente tiene saldo pendiente.
Uso: cd ~/inventario/static && python3 fix_borrar_cliente.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src

# ================================================================
# 1. Agregar el boton en el modal-footer del detalle
# ================================================================
viejo = '''    <div class="modal-footer">
      <button onclick="abrirEditarCliente()">✏️ Editar</button>
      <button onclick="cerrarDetalle()">Cerrar</button>
    </div>'''

nuevo = '''    <div class="modal-footer">
      <button onclick="abrirEditarCliente()">✏️ Editar</button>
      <button onclick="eliminarClienteActual()" id="btn-eliminar-cliente" style="color:var(--red);display:none">🗑 Eliminar</button>
      <button onclick="cerrarDetalle()">Cerrar</button>
    </div>'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("1. Boton de eliminar agregado al modal")
else:
    print("1. ADVERTENCIA: no se encontro el modal-footer exacto (coincidencias: " + str(n) + ")")

# ================================================================
# 2. Agregar la funcion eliminarClienteActual() y mostrar el boton
#    solo si el usuario logueado es gerente
# ================================================================
if 'function eliminarClienteActual' not in src:
    funcion = '''
async function eliminarClienteActual(){
  const c = clientesCache.find(x=>x.id===clienteActualId);
  const nombre = c ? c.nombre : 'este cliente';
  if(!confirm('¿Eliminar a ' + nombre + '? Esta acción no se puede deshacer.\\n\\nSolo se puede eliminar si no tiene saldo pendiente.')) return;
  try{
    const r = await authFetch('/api/clientes/'+clienteActualId, {method:'DELETE'});
    if(r.status===204){
      cerrarDetalle();
      cargarClientes();
    }else{
      const data = await r.json();
      alert(data.detail||'No se pudo eliminar');
    }
  }catch(e){
    alert('Error de conexión');
  }
}

'''
    marcador = 'function cerrarDetalle(){'
    if marcador in src:
        src = src.replace(marcador, funcion + marcador, 1)
        print("2. Funcion eliminarClienteActual() agregada")
    else:
        print("2. ERROR: no se encontro 'function cerrarDetalle(){'")

# Mostrar el boton solo si el rol es gerente (el backend ya lo exige,
# esto solo evita que un cajero vea un boton que no puede usar)
if "sesionActual.rol === 'gerente'" not in src:
    marcador2 = 'requireAuth();'
    if marcador2 in src:
        codigo_rol = '''requireAuth();

const _sesionActual = getSesion();
if(_sesionActual && _sesionActual.rol === 'gerente'){
  const _btnElim = document.getElementById('btn-eliminar-cliente');
  if(_btnElim) _btnElim.style.display = 'inline-block';
}'''
        src = src.replace(marcador2, codigo_rol, 1)
        print("3. Visibilidad del boton restringida a gerentes")
    else:
        print("3. ADVERTENCIA: no se encontro 'requireAuth();'")

if src != original:
    open(CLIENTES, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Los gerentes ya veran el boton Eliminar en el detalle de cada cliente.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
