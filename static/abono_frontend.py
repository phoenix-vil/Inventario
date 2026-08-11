#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1. Muestra pagado/saldo por venta especifica en el detalle del cliente.
2. Agrega un modal de recibo (descargar/imprimir/WhatsApp) tras registrar
   un abono.
Corre DESPUES de abono_backend.py
Uso: cd ~/inventario/static && python3 abono_frontend.py
"""
import os, re

CLIENTES = os.path.expanduser('~/inventario/static/clientes.html')
src = open(CLIENTES, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Mostrar saldo por venta en vez de solo el total
# ================================================================
viejo_ventas = '''    ventasCont.innerHTML = c.ventas.length
      ? c.ventas.map(v=>{
          const fecha = new Date(v.fecha).toLocaleDateString('es-MX',{day:'numeric',month:'short',year:'numeric'});
          return `<div class="hist-row"><span>Venta #${v.id}<div class="hist-fecha">${fecha}</div></span><span>${money(v.total)}</span></div>`;
        }).join('')
      : '<div style="font-size:12px;color:var(--text2);padding:6px 0">Sin ventas a crédito</div>';'''

nuevo_ventas = '''    ventasCont.innerHTML = c.ventas.length
      ? c.ventas.map(v=>{
          const fecha = new Date(v.fecha).toLocaleDateString('es-MX',{day:'numeric',month:'short',year:'numeric'});
          const saldoV = (v.saldo!=null) ? v.saldo : v.total;
          const detalle = saldoV>0
            ? `<span>${money(v.total)}<div class="hist-fecha" style="color:var(--red);text-align:right">Debe ${money(saldoV)}</div></span>`
            : `<span style="color:var(--green)">${money(v.total)} ✓ pagada</span>`;
          return `<div class="hist-row"><span>Venta #${v.id}<div class="hist-fecha">${fecha}</div></span>${detalle}</div>`;
        }).join('')
      : '<div style="font-size:12px;color:var(--text2);padding:6px 0">Sin ventas a crédito</div>';'''

n1 = src.count(viejo_ventas)
if n1 == 1:
    src = src.replace(viejo_ventas, nuevo_ventas, 1)
    cambios.append('saldo por venta agregado al detalle del cliente')
elif 'Debe ' in src:
    print("* Ya estaba actualizado")
else:
    print("ERROR: no se encontro el bloque exacto de renderizado de ventas")

# ================================================================
# 2. Modal de recibo (HTML), antes de </body>
# ================================================================
if 'modal-recibo' not in src:
    modal_recibo = '''
<!-- Modal de recibo de abono -->
<div class="overlay" id="modal-recibo">
  <div class="modal">
    <h2>✅ Abono registrado</h2>
    <div id="recibo-contenido" style="background:var(--bg);border-radius:10px;padding:1.25rem;margin-bottom:1rem;font-family:ui-monospace,monospace;font-size:13px;white-space:pre-line"></div>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <button onclick="descargarRecibo()" style="flex:1;height:42px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);cursor:pointer;font-size:13px">⬇ Descargar</button>
      <button onclick="imprimirRecibo()" style="flex:1;height:42px;border:0.5px solid var(--border);border-radius:8px;background:transparent;color:var(--text);cursor:pointer;font-size:13px">🖨 Imprimir</button>
    </div>
    <button onclick="compartirReciboWhatsApp()" style="width:100%;height:42px;border:0.5px solid #25d366;border-radius:8px;background:#e9fbe9;color:#1a6e38;cursor:pointer;font-size:13px;font-weight:600;margin-bottom:8px">💬 Compartir por WhatsApp</button>
    <div class="modal-footer">
      <button class="primary" onclick="cerrarRecibo()">Cerrar</button>
    </div>
  </div>
</div>
'''
    if '</body>' in src:
        src = src.replace('</body>', modal_recibo + '\n</body>', 1)
        cambios.append('modal de recibo agregado (HTML)')
    else:
        print("ERROR: no se encontro </body>")

# ================================================================
# 3. Funciones JS del recibo
# ================================================================
if 'function generarTextoRecibo' not in src:
    funciones_recibo = '''
let reciboActual = null;

function generarTextoRecibo(v){
  const fecha = new Date(v.fecha).toLocaleString('es-MX');
  let txt = '🏪 ONLY ENTERPRISES\\n';
  txt += 'Recibo de abono\\n';
  txt += '─────────────────────\\n';
  txt += 'Cliente: ' + v.cliente_nombre + '\\n';
  txt += 'Fecha: ' + fecha + '\\n';
  if(v.operador) txt += 'Atendió: ' + v.operador + '\\n';
  if(v.sucursal) txt += 'Sucursal: ' + v.sucursal + '\\n';
  txt += '─────────────────────\\n';
  txt += 'Monto abonado: ' + money(v.monto) + '\\n';
  txt += 'Método: ' + v.metodo_pago + '\\n';
  if(v.nota) txt += 'Nota: ' + v.nota + '\\n';
  txt += '─────────────────────\\n';
  txt += 'Saldo restante: ' + money(v.saldo_restante) + '\\n';
  txt += '\\n¡Gracias por su pago!';
  return txt;
}

function mostrarRecibo(data){
  reciboActual = data;
  document.getElementById('recibo-contenido').textContent = generarTextoRecibo(data);
  document.getElementById('modal-recibo').classList.add('open');
}

function cerrarRecibo(){
  document.getElementById('modal-recibo').classList.remove('open');
}

function descargarRecibo(){
  if(!reciboActual) return;
  const txt = generarTextoRecibo(reciboActual);
  const blob = new Blob([txt], {type:'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'abono_' + reciboActual.id + '.txt';
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

function imprimirRecibo(){
  if(!reciboActual) return;
  const win = window.open('', '_blank');
  const txtHtml = generarTextoRecibo(reciboActual).replace(/\\n/g,'<br>');
  win.document.write('<html><head><title>Recibo de abono</title><style>body{font-family:monospace;font-size:13px;max-width:300px;margin:20px auto}</style></head><body>' + txtHtml + '</body></html>');
  win.document.close();
  setTimeout(function(){win.print();}, 300);
}

function compartirReciboWhatsApp(){
  if(!reciboActual) return;
  const txt = generarTextoRecibo(reciboActual);
  window.open('https://wa.me/?text=' + encodeURIComponent(txt), '_blank');
}

'''
    marcador = 'async function abrirDetalle(id){'
    if marcador in src:
        src = src.replace(marcador, funciones_recibo + marcador, 1)
        cambios.append('funciones JS del recibo agregadas')
    else:
        print("ERROR: no se encontro 'async function abrirDetalle(id){'")
else:
    print("* Las funciones del recibo ya existian")

# ================================================================
# 4. confirmarAbono(): mostrar el recibo tras confirmar
# ================================================================
viejo_confirmar = '''    document.getElementById('form-abono').style.display='none';
    abrirDetalle(clienteActualId);
    cargarClientes();
  }catch(e){
    msg.className='msg error show'; msg.textContent='Error de conexión';
  }
}
document.addEventListener('keydown', e=>{'''

nuevo_confirmar = '''    document.getElementById('form-abono').style.display='none';
    abrirDetalle(clienteActualId);
    cargarClientes();
    mostrarRecibo(data);
  }catch(e){
    msg.className='msg error show'; msg.textContent='Error de conexión';
  }
}
document.addEventListener('keydown', e=>{'''

n3 = src.count(viejo_confirmar)
if n3 == 1:
    src = src.replace(viejo_confirmar, nuevo_confirmar, 1)
    cambios.append('confirmarAbono() ahora muestra el recibo')
elif 'mostrarRecibo(data);' in src:
    print("* confirmarAbono ya mostraba el recibo")
else:
    print("ERROR: no se encontro el bloque exacto de confirmarAbono")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(CLIENTES, 'w', encoding='utf-8').write(src)
    print()
    for c in cambios:
        print("OK " + c)
else:
    print("No se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Prueba registrar un abono: debe verse el desglose de saldo")
    print("por venta y aparecer el recibo con opciones de descargar/imprimir/WhatsApp.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
