#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega la tarjeta "Abonos cobrados" y la lista detallada dentro del
Historial de ventas, usando los mismos filtros de fecha/sucursal.
Corre DESPUES de abonos_historial_backend.py
Uso: cd ~/inventario/static && python3 abonos_historial_frontend.py
"""
import os, re

HIST = os.path.expanduser('~/inventario/static/historial.html')
src = open(HIST, encoding='utf-8').read()
original = src
cambios = []

# ================================================================
# 1. Agregar la tarjeta de stat "Abonos cobrados"
# ================================================================
viejo_stats = '''    <div class="stat"><div class="stat-label">Tarjeta</div><div class="stat-value" id="s-tarjeta">—</div></div>
    <div class="stat"><div class="stat-label">Ticket promedio</div><div class="stat-value" id="s-prom">—</div></div>
  </div>'''

nuevo_stats = '''    <div class="stat"><div class="stat-label">Tarjeta</div><div class="stat-value" id="s-tarjeta">—</div></div>
    <div class="stat"><div class="stat-label">Ticket promedio</div><div class="stat-value" id="s-prom">—</div></div>
    <div class="stat"><div class="stat-label">💰 Abonos cobrados</div><div class="stat-value" id="s-abonos" style="color:var(--blue)">—</div></div>
  </div>'''

n1 = src.count(viejo_stats)
if n1 == 1:
    src = src.replace(viejo_stats, nuevo_stats, 1)
    cambios.append('tarjeta de Abonos cobrados agregada')
elif 's-abonos' in src:
    print("* La tarjeta ya existia")
else:
    print("ERROR: no se encontro el bloque exacto de stats")

# ================================================================
# 2. Agregar la seccion de lista de abonos (despues del desglose
#    por sucursal existente)
# ================================================================
viejo_lista = '''  <div class="lista" id="lista"></div>
  <div class="section-title" id="op-titulo" style="font-size:13px;font-weight:600;color:var(--text2);margin:1.5rem 0 .75rem;text-transform:uppercase;letter-spacing:.5px;display:none">Ventas por operador</div>
  <div class="card" id="op-desglose" style="display:none"></div>'''

nuevo_lista = '''  <div class="lista" id="lista"></div>
  <div class="section-title" id="abonos-titulo" style="font-size:13px;font-weight:600;color:var(--text2);margin:1.5rem 0 .75rem;text-transform:uppercase;letter-spacing:.5px;display:none">💰 Abonos de crédito cobrados en este período</div>
  <div class="card" id="abonos-lista" style="display:none"></div>
  <div class="section-title" id="op-titulo" style="font-size:13px;font-weight:600;color:var(--text2);margin:1.5rem 0 .75rem;text-transform:uppercase;letter-spacing:.5px;display:none">Ventas por operador</div>
  <div class="card" id="op-desglose" style="display:none"></div>'''

n2 = src.count(viejo_lista)
if n2 == 1:
    src = src.replace(viejo_lista, nuevo_lista, 1)
    cambios.append('seccion de lista de abonos agregada al HTML')
elif 'abonos-lista' in src:
    print("* La seccion ya existia")
else:
    print("ERROR: no se encontro el bloque exacto de la lista")

# ================================================================
# 3. cargar(): pedir tambien los abonos del periodo y pintarlos
# ================================================================
viejo_cargar = '''  try{
    const [rv,rs]=await Promise.all([
      authFetch('/api/ventas?'+params.toString()),
      authFetch('/api/ventas/resumen?'+params.toString())
    ]);
    ventas=await rv.json();
    const resumen=await rs.json();
    document.getElementById('s-num').textContent=resumen.num_ventas;
    document.getElementById('s-total').textContent=money(resumen.total_vendido);
    document.getElementById('s-efectivo').textContent=money(resumen.total_efectivo||0);
    document.getElementById('s-tarjeta').textContent=money(resumen.total_tarjeta||0);
    document.getElementById('s-prom').textContent=money(resumen.ticket_promedio);
    renderDesglose(resumen.por_operador||[]);
    renderDesgloseSucursal(resumen.por_sucursal||[]);
    render();
  }catch(e){console.error(e);}
}'''

nuevo_cargar = '''  try{
    const [rv,rs,ra]=await Promise.all([
      authFetch('/api/ventas?'+params.toString()),
      authFetch('/api/ventas/resumen?'+params.toString()),
      authFetch('/api/clientes/abonos-periodo?'+params.toString())
    ]);
    ventas=await rv.json();
    const resumen=await rs.json();
    document.getElementById('s-num').textContent=resumen.num_ventas;
    document.getElementById('s-total').textContent=money(resumen.total_vendido);
    document.getElementById('s-efectivo').textContent=money(resumen.total_efectivo||0);
    document.getElementById('s-tarjeta').textContent=money(resumen.total_tarjeta||0);
    document.getElementById('s-prom').textContent=money(resumen.ticket_promedio);
    renderDesglose(resumen.por_operador||[]);
    renderDesgloseSucursal(resumen.por_sucursal||[]);
    if(ra.ok){
      const abonosData=await ra.json();
      document.getElementById('s-abonos').textContent=money(abonosData.total||0);
      renderAbonos(abonosData.abonos||[]);
    }
    render();
  }catch(e){console.error(e);}
}

function renderAbonos(lista){
  const titulo=document.getElementById('abonos-titulo');
  const cont=document.getElementById('abonos-lista');
  if(!lista.length){titulo.style.display='none';cont.style.display='none';return;}
  titulo.style.display='block';
  cont.style.display='block';
  cont.innerHTML=lista.map(a=>{
    const fecha=new Date(a.fecha).toLocaleString('es-MX',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
    return `<div class="hist-row" style="display:flex;justify-content:space-between;padding:.75rem 1rem;border-bottom:0.5px solid var(--border)">
      <span>👤 ${esc(a.cliente_nombre)}${a.nota?' · '+esc(a.nota):''}<div style="font-size:11px;color:var(--text2)">${fecha} · ${esc(a.operador||'')}${a.sucursal?' · Suc. '+esc(a.sucursal):''}</div></span>
      <span style="color:var(--blue);font-weight:600">+${money(a.monto)}</span>
    </div>`;
  }).join('');
}'''

n3 = src.count(viejo_cargar)
if n3 == 1:
    src = src.replace(viejo_cargar, nuevo_cargar, 1)
    cambios.append('cargar() ahora incluye abonos, y renderAbonos() agregada')
elif 'function renderAbonos' in src:
    print("* cargar() ya estaba actualizado")
else:
    print("ERROR: no se encontro el bloque exacto de cargar()")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(HIST, 'w', encoding='utf-8').write(src)
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
    print("Listo. El Historial ahora muestra los abonos de credito cobrados")
    print("en el mismo periodo filtrado, con su propia tarjeta y lista detallada.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
