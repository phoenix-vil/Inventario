#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Frontend de "marcar como vendida":
 1. pagos.html: guarda el ID de la cotizacion de origen al importarla,
    y al cobrar exitosamente, marca esa cotizacion como vendida.
 2. cotizaciones.html: distintivo "Vendida" en el historial y ultimas
    cotizaciones; bloquea "Cobrar en Punto de Venta" si ya se vendio.
 3. cotizaciones.html: empareja el alto de todos los botones de la
    pantalla "Cotizacion generada" (46px -> 44px en el de WhatsApp).
Uso: cd ~/inventario-qa/static && python3 qa_marcar_vendida_frontend.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')
res = []

# ============================================================
# 1a. pagos.html: variable global + guardarla al importar
# ============================================================
PAGOS = os.path.join(STATIC, 'pagos.html')
src = open(PAGOS, encoding='utf-8').read()

viejo1 = '''(function(){
  const params = new URLSearchParams(window.location.search);
  const cotId = params.get('cotizacion');
  if(cotId) importarCotizacion(cotId);
})();'''
nuevo1 = '''let cotizacionOrigenId = null;
(function(){
  const params = new URLSearchParams(window.location.search);
  const cotId = params.get('cotizacion');
  if(cotId){ cotizacionOrigenId = cotId; importarCotizacion(cotId); }
})();'''
if viejo1 in src:
    src = src.replace(viejo1, nuevo1, 1)
    res.append("OK pagos.html: cotizacionOrigenId se guarda al importar")
elif 'let cotizacionOrigenId' in src:
    res.append("* pagos.html: cotizacionOrigenId ya existia")
else:
    res.append("ERROR pagos.html: no se encontro el bloque de lectura de ?cotizacion=")

# ============================================================
# 1b. pagos.html: marcar vendida tras cobrar con exito
# ============================================================
viejo2 = '''    cerrarCobro();
    carrito=[];descuentoExtra=0;autorizadoPor=null;
    renderCarrito();
    mostrarTicket(data);
  }catch(e){msg.className='msg error show';msg.textContent='Error de conexión';}
}'''
nuevo2 = '''    cerrarCobro();
    carrito=[];descuentoExtra=0;autorizadoPor=null;
    renderCarrito();
    mostrarTicket(data);
    if(cotizacionOrigenId){
      try{
        await authFetch('/api/cotizaciones/'+cotizacionOrigenId+'/marcar-vendida', {
          method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({venta_id:data.id})
        });
      }catch(e){}
      cotizacionOrigenId = null;
    }
  }catch(e){msg.className='msg error show';msg.textContent='Error de conexión';}
}'''
if viejo2 in src:
    src = src.replace(viejo2, nuevo2, 1)
    res.append("OK pagos.html: la cotizacion se marca vendida al cobrar exitosamente")
elif "cotizaciones/'+cotizacionOrigenId+'/marcar-vendida" in src:
    res.append("* pagos.html: ya se marcaba al cobrar")
else:
    res.append("ERROR pagos.html: no se encontro el bloque de exito de confirmarCobro")

open(PAGOS, 'w', encoding='utf-8').write(src)

# ============================================================
# 2. cotizaciones.html: distintivo "Vendida" + bloqueo del boton
# ============================================================
COT = os.path.join(STATIC, 'cotizaciones.html')
src2 = open(COT, encoding='utf-8').read()

# 2a. Historial: distintivo
viejo3 = '''      return `<div class="hist-item" onclick="verCotizacion(${c.id})">
        <div>
          <div class="h-id">#${c.id}${c.cliente_nombre?' · '+esc(c.cliente_nombre):''}</div>
          <div class="h-meta">${fecha} · ${c.num_items} artículo${c.num_items!==1?'s':''} · ${esc(c.operador||'')}</div>
        </div>
        <div class="h-total">${money(c.total)}</div>
      </div>`;'''
nuevo3 = '''      const badgeVendida = c.venta_id ? ' <span style="font-size:10px;font-weight:700;color:var(--green);background:var(--green-bg);padding:1px 6px;border-radius:5px">Vendida</span>' : '';
      return `<div class="hist-item" onclick="verCotizacion(${c.id})">
        <div>
          <div class="h-id">#${c.id}${c.cliente_nombre?' · '+esc(c.cliente_nombre):''}${badgeVendida}</div>
          <div class="h-meta">${fecha} · ${c.num_items} artículo${c.num_items!==1?'s':''} · ${esc(c.operador||'')}</div>
        </div>
        <div class="h-total">${money(c.total)}</div>
      </div>`;'''
n3 = src2.count(viejo3)
if n3 == 1:
    src2 = src2.replace(viejo3, nuevo3, 1)
    res.append("OK cotizaciones.html: distintivo 'Vendida' en el historial")
elif 'badgeVendida' in src2:
    res.append("* cotizaciones.html: el distintivo ya estaba en algun lugar")
else:
    res.append("ERROR cotizaciones.html: no se encontro el bloque del historial (coincidencias: " + str(n3) + ")")

# 2b. Ultimas cotizaciones (bienvenida): mismo distintivo
viejo4 = '''      return `<div class="hist-item" onclick="verCotizacion(${c.id})">
        <div>
          <div class="h-id">#${c.id}${c.cliente_nombre?' · '+esc(c.cliente_nombre):''}</div>
          <div class="h-meta">${fecha} · ${c.num_items} artículo${c.num_items!==1?'s':''}</div>
        </div>
        <div class="h-total">${money(c.total)}</div>
      </div>`;'''
nuevo4 = '''      const badgeVendida = c.venta_id ? ' <span style="font-size:10px;font-weight:700;color:var(--green);background:var(--green-bg);padding:1px 6px;border-radius:5px">Vendida</span>' : '';
      return `<div class="hist-item" onclick="verCotizacion(${c.id})">
        <div>
          <div class="h-id">#${c.id}${c.cliente_nombre?' · '+esc(c.cliente_nombre):''}${badgeVendida}</div>
          <div class="h-meta">${fecha} · ${c.num_items} artículo${c.num_items!==1?'s':''}</div>
        </div>
        <div class="h-total">${money(c.total)}</div>
      </div>`;'''
if viejo4 in src2:
    src2 = src2.replace(viejo4, nuevo4, 1)
    res.append("OK cotizaciones.html: distintivo 'Vendida' en ultimas cotizaciones")
elif src2.count('badgeVendida') >= 2:
    res.append("* cotizaciones.html: ya estaba en ultimas cotizaciones tambien")

# 2c. Bloquear "Cobrar en Punto de Venta" si ya se vendio (en tkMostrar/verCotizacion)
viejo5 = '''function tkMostrar(v){
  tkActual = v;
  tkBlobActual = null;
  document.getElementById('tk-resumen-id').textContent = 'Cotización #' + v.id + (v.cliente_nombre ? ' · ' + v.cliente_nombre : '');
  document.getElementById('tk-resumen-total').textContent = money(v.total);
  document.getElementById('tk-modal').classList.add('open');
}'''
nuevo5 = '''function tkActualizarBotonCobrar(v){
  const btn = document.getElementById('btn-cobrar-pos');
  if(!btn) return;
  if(v.venta_id){
    btn.disabled = true;
    btn.textContent = '✅ Ya vendida (venta #' + v.venta_id + ')';
    btn.style.opacity = '.6';
    btn.style.cursor = 'not-allowed';
  }else{
    btn.disabled = false;
    btn.textContent = '💳 Cobrar en Punto de Venta';
    btn.style.opacity = '1';
    btn.style.cursor = 'pointer';
  }
}
function tkMostrar(v){
  tkActual = v;
  tkBlobActual = null;
  document.getElementById('tk-resumen-id').textContent = 'Cotización #' + v.id + (v.cliente_nombre ? ' · ' + v.cliente_nombre : '');
  document.getElementById('tk-resumen-total').textContent = money(v.total);
  tkActualizarBotonCobrar(v);
  document.getElementById('tk-modal').classList.add('open');
}'''
if viejo5 in src2:
    src2 = src2.replace(viejo5, nuevo5, 1)
    res.append("OK cotizaciones.html: boton se bloquea si la cotizacion ya fue vendida")
elif 'function tkActualizarBotonCobrar' in src2:
    res.append("* cotizaciones.html: el bloqueo ya existia")
else:
    res.append("ERROR cotizaciones.html: no se encontro tkMostrar")

# Actualizar tambien en generarCotizacion() (recien creada, nunca esta vendida, pero por consistencia)
viejo5b = '''    tkActual = data;
    tkBlobActual = null;
    document.getElementById('tk-resumen-id').textContent = 'Cotización #' + data.id + (data.cliente_nombre ? ' · ' + data.cliente_nombre : '');
    document.getElementById('tk-resumen-total').textContent = money(data.total);
    irPaso(3);'''
nuevo5b = '''    tkActual = data;
    tkBlobActual = null;
    document.getElementById('tk-resumen-id').textContent = 'Cotización #' + data.id + (data.cliente_nombre ? ' · ' + data.cliente_nombre : '');
    document.getElementById('tk-resumen-total').textContent = money(data.total);
    tkActualizarBotonCobrar(data);
    irPaso(3);'''
if viejo5b in src2:
    src2 = src2.replace(viejo5b, nuevo5b, 1)
    res.append("OK cotizaciones.html: boton actualizado tambien al generar")
elif 'tkActualizarBotonCobrar(data)' in src2:
    res.append("* cotizaciones.html: ya estaba en generarCotizacion")

# Agregar id al boton para poder controlarlo
viejo5c = '<button class="tk-btn-sec" onclick="cobrarEnPOS()" style="width:100%;flex:none">💳 Cobrar en Punto de Venta</button>'
nuevo5c = '<button class="tk-btn-sec" id="btn-cobrar-pos" onclick="cobrarEnPOS()" style="width:100%;flex:none">💳 Cobrar en Punto de Venta</button>'
if viejo5c in src2:
    src2 = src2.replace(viejo5c, nuevo5c, 1)
    res.append("OK cotizaciones.html: id agregado al boton de cobrar")
elif 'id="btn-cobrar-pos"' in src2:
    res.append("* cotizaciones.html: el id ya estaba")
else:
    res.append("ERROR cotizaciones.html: no se encontro el boton de cobrar exacto")

# Que cobrarEnPOS() no haga nada si ya esta vendida (defensa extra del lado cliente)
viejo5d = '''function cobrarEnPOS(){
  if(!tkActual) return;
  window.location.href = '/pagos?cotizacion=' + tkActual.id;
}'''
nuevo5d = '''function cobrarEnPOS(){
  if(!tkActual || tkActual.venta_id) return;
  window.location.href = '/pagos?cotizacion=' + tkActual.id;
}'''
if viejo5d in src2:
    src2 = src2.replace(viejo5d, nuevo5d, 1)
    res.append("OK cotizaciones.html: cobrarEnPOS() bloqueado si ya esta vendida")
elif 'tkActual.venta_id) return;' in src2:
    res.append("* cotizaciones.html: cobrarEnPOS ya estaba protegido")
else:
    res.append("ERROR cotizaciones.html: no se encontro la funcion cobrarEnPOS")

# ============================================================
# 3. Parejar el alto del boton de WhatsApp (46px -> 44px)
# ============================================================
viejo6 = '.tk-btn-wa{width:100%;height:46px;'
nuevo6 = '.tk-btn-wa{width:100%;height:44px;'
if viejo6 in src2:
    src2 = src2.replace(viejo6, nuevo6, 1)
    res.append("OK cotizaciones.html: alto de WhatsApp igualado a 44px (como los demas)")
elif 'height:44px' in src2 and '.tk-btn-wa{' in src2:
    res.append("* cotizaciones.html: el alto ya estaba igualado")

open(COT, 'w', encoding='utf-8').write(src2)

print()
for r in res:
    print(r)

ok_total = True
print()
for ruta in [PAGOS, COT]:
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + os.path.basename(ruta) + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 58)
if ok_total and not any(r.startswith('ERROR') for r in res):
    print("Ambos son cambios de HTML/JS, no requieren reiniciar el servicio.")
    print("Prueba con Ctrl+Shift+R.")
else:
    print("Revisa los mensajes de arriba antes de probar.")
