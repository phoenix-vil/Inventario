#!/usr/bin/env python3
"""
1. Abrevia "Sucursal" -> "Suc." en el badge del topbar (evita desborde en móvil)
2. Agrega botón de TRASLADO de stock entre sucursales en inv_sucursales.html
   + endpoint /api/stock-sucursal/trasladar en el backend

Uso: cd ~/inventario && python3 fix_abrev_traslado.py
"""
import os, re

BASE   = os.path.expanduser('~/inventario')
STATIC = os.path.join(BASE, 'static')

# ══ 1. Abreviar "Sucursal" en el badge del menú ═════════════════════════════
print("1. Abreviando 'Sucursal' -> 'Suc.' en el badge del topbar...")
menu = os.path.join(STATIC, 'menu.html')
src = open(menu, encoding='utf-8').read()
antes = src
src = src.replace(
    "_suc.textContent = '🏪 Sucursal ' + sesion.sucursal;",
    "_suc.textContent = '🏪 Suc. ' + sesion.sucursal;"
)
if src != antes:
    open(menu,'w',encoding='utf-8').write(src)
    print("   ✓ Badge ahora dice 'Suc.' en vez de 'Sucursal'")
else:
    print("   • No se encontró el texto exacto (puede que ya esté abreviado)")

# ══ 2. Backend: endpoint de traslado entre sucursales ══════════════════════
print("2. Agregando endpoint de traslado al backend...")
main_py = os.path.join(BASE, 'main.py')
src = open(main_py, encoding='utf-8').read()

if '/api/stock-sucursal/trasladar' not in src:
    # Insertar el esquema TrasladoStock si no existe en schemas.py
    schemas_py = os.path.join(BASE, 'schemas.py')
    ssrc = open(schemas_py, encoding='utf-8').read()
    if 'class TrasladoStock' not in ssrc:
        ssrc += '''

class TrasladoStock(BaseModel):
    producto_id: int
    sucursal_origen: str
    sucursal_destino: str
    cantidad: float = Field(..., gt=0)
'''
        open(schemas_py, 'w', encoding='utf-8').write(ssrc)
        print("   ✓ Esquema TrasladoStock agregado a schemas.py")

    # Importar el esquema en main.py
    if 'TrasladoStock' not in src:
        src = re.sub(
            r'(from schemas import \([^)]*)\)',
            r'\1, TrasladoStock)',
            src, count=1
        )

    # Insertar el endpoint después de asignar_stock (POST /api/stock-sucursal)
    endpoint = '''

@app.post("/api/stock-sucursal/trasladar")
def trasladar_stock(data: TrasladoStock, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    if data.sucursal_origen == data.sucursal_destino:
        raise HTTPException(status_code=400, detail="La sucursal de origen y destino no pueden ser la misma")

    p = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    origen = db.query(StockSucursal).filter(
        StockSucursal.producto_id == data.producto_id,
        StockSucursal.sucursal == data.sucursal_origen
    ).first()
    stock_origen = origen.cantidad if origen else 0

    if data.cantidad > stock_origen:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente en Suc. {data.sucursal_origen} (disponible: {round(stock_origen,3)})"
        )

    # Restar de origen
    origen.cantidad = round(origen.cantidad - data.cantidad, 3)
    origen.actualizado_en = datetime.utcnow()

    # Sumar a destino (upsert)
    destino = db.query(StockSucursal).filter(
        StockSucursal.producto_id == data.producto_id,
        StockSucursal.sucursal == data.sucursal_destino
    ).first()
    if destino:
        destino.cantidad = round(destino.cantidad + data.cantidad, 3)
        destino.actualizado_en = datetime.utcnow()
    else:
        db.add(StockSucursal(
            producto_id=data.producto_id,
            sucursal=data.sucursal_destino,
            cantidad=data.cantidad,
            actualizado_en=datetime.utcnow()
        ))

    db.commit()
    return {
        "producto_id": data.producto_id,
        "producto_nombre": p.nombre,
        "sucursal_origen": data.sucursal_origen,
        "sucursal_destino": data.sucursal_destino,
        "cantidad_trasladada": data.cantidad,
        "stock_restante_origen": round(stock_origen - data.cantidad, 3),
    }
'''
    # Insertar justo después del endpoint POST /api/stock-sucursal existente
    marcador = re.search(r'@app\.post\("/api/stock-sucursal"\).*?\n\n\n', src, re.DOTALL)
    if marcador:
        idx = marcador.end()
        src = src[:idx] + endpoint.lstrip('\n') + '\n\n' + src[idx:]
    else:
        # Insertar al final del archivo si no se encuentra el marcador
        src = src.rstrip() + '\n' + endpoint + '\n'

    open(main_py, 'w', encoding='utf-8').write(src)
    print("   ✓ Endpoint POST /api/stock-sucursal/trasladar agregado")
else:
    print("   • El endpoint ya existía")

# ══ 3. Frontend: botón de traslado en inv_sucursales.html ══════════════════
print("3. Agregando botón de traslado en Inventario por sucursal...")
inv = os.path.join(STATIC, 'inv_sucursales.html')
src = open(inv, encoding='utf-8').read()

if 'abrirTraslado' not in src:
    # 3a. Agregar botón en el topbar (junto a escáner/CSV/actualizar)
    src = src.replace(
        '<button class="icon-btn" onclick="abrirEscaner()" title="Escanear código">📷</button>',
        '<button class="icon-btn" onclick="abrirEscaner()" title="Escanear código">📷</button>\n    <button onclick="abrirTraslado()" class="icon-btn" title="Trasladar stock entre sucursales" style="width:auto;padding:0 10px;font-size:12px">🔄 Trasladar</button>'
    )

    # 3b. Agregar el modal de traslado antes del modal de escáner
    modal_traslado = '''
<!-- Modal traslado de stock entre sucursales -->
<div class="overlay" id="modal-traslado">
  <div class="modal">
    <h2>🔄 Trasladar stock entre sucursales</h2>
    <div class="field">
      <label>Producto</label>
      <input type="text" id="tr-buscar" placeholder="Buscar producto..." oninput="filtrarTraslado()" autocomplete="off">
      <div id="tr-resultados" style="max-height:160px;overflow-y:auto;margin-top:6px"></div>
      <div id="tr-seleccionado" style="display:none;margin-top:8px;padding:.625rem .875rem;background:var(--blue-bg);border-radius:8px;font-size:13px;color:var(--blue);font-weight:600"></div>
    </div>
    <div class="field">
      <label>De la sucursal</label>
      <select id="tr-origen" onchange="actualizarStockOrigen()"></select>
    </div>
    <div class="field">
      <label>A la sucursal</label>
      <select id="tr-destino"></select>
    </div>
    <div class="field">
      <label>Cantidad a trasladar</label>
      <input type="number" id="tr-cantidad" min="0" step="1" placeholder="0">
      <div id="tr-disponible" style="font-size:12px;color:var(--text2);margin-top:4px"></div>
    </div>
    <div class="scan-msg" id="tr-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarTraslado()">Cancelar</button>
      <button class="primary" onclick="confirmarTraslado()" style="background:var(--blue);color:#fff;border:none">Trasladar</button>
    </div>
  </div>
</div>

'''
    src = src.replace('<!-- Modal escáner -->', modal_traslado + '<!-- Modal escáner -->')

    # 3c. Agregar la lógica JS al final, antes de cargar()
    js_traslado = '''
/* ── Traslado de stock entre sucursales ─────────────────────────────────── */
let trProductoSel = null;

function abrirTraslado(){
  if(!data || !data.sucursales.length){
    toast('Necesitas al menos 2 sucursales registradas para trasladar', true);
    return;
  }
  if(data.sucursales.length < 2){
    toast('Necesitas al menos 2 sucursales para poder trasladar stock', true);
    return;
  }
  trProductoSel = null;
  document.getElementById('tr-buscar').value = '';
  document.getElementById('tr-resultados').innerHTML = '';
  document.getElementById('tr-seleccionado').style.display = 'none';
  document.getElementById('tr-cantidad').value = '';
  document.getElementById('tr-msg').className = 'scan-msg';

  const origSel = document.getElementById('tr-origen');
  const destSel = document.getElementById('tr-destino');
  origSel.innerHTML = data.sucursales.map(s=>`<option value="${esc(s)}">Suc. ${esc(s)}</option>`).join('');
  destSel.innerHTML = data.sucursales.map(s=>`<option value="${esc(s)}">Suc. ${esc(s)}</option>`).join('');
  if(data.sucursales.length>1) destSel.value = data.sucursales[1];

  document.getElementById('modal-traslado').classList.add('open');
  actualizarStockOrigen();
}

function cerrarTraslado(){
  document.getElementById('modal-traslado').classList.remove('open');
  trProductoSel = null;
}

function filtrarTraslado(){
  const q = document.getElementById('tr-buscar').value.toLowerCase().trim();
  const cont = document.getElementById('tr-resultados');
  if(!q || !data){ cont.innerHTML=''; return; }
  const encontrados = data.productos.filter(p=>
    p.nombre.toLowerCase().includes(q) || (p.marca||'').toLowerCase().includes(q) || (p.codigo_barras||'')===q
  ).slice(0, 8);
  if(!encontrados.length){ cont.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:6px 0">Sin resultados</div>'; return; }
  cont.innerHTML = encontrados.map(p=>`
    <div onclick='seleccionarProductoTraslado(${p.id})' style="padding:8px 10px;border:0.5px solid var(--border);border-radius:8px;margin-bottom:4px;cursor:pointer;font-size:13px" onmouseover="this.style.background='var(--bg)'" onmouseout="this.style.background='transparent'">
      <strong>${esc(p.nombre)}</strong>${p.marca?' · '+esc(p.marca):''}
    </div>`).join('');
}

function seleccionarProductoTraslado(id){
  trProductoSel = data.productos.find(p=>p.id===id);
  if(!trProductoSel) return;
  document.getElementById('tr-buscar').value = '';
  document.getElementById('tr-resultados').innerHTML = '';
  const sel = document.getElementById('tr-seleccionado');
  sel.style.display = 'block';
  sel.textContent = '📦 ' + trProductoSel.nombre;
  actualizarStockOrigen();
}

function actualizarStockOrigen(){
  const disp = document.getElementById('tr-disponible');
  if(!trProductoSel){ disp.textContent=''; return; }
  const origen = document.getElementById('tr-origen').value;
  const d = trProductoSel.por_sucursal[origen] || {asignado:0, vendido:0};
  const restante = Math.round((d.asignado - d.vendido)*1000)/1000;
  const unidad = trProductoSel.vendido_por_peso ? ' kg' : '';
  disp.textContent = `Disponible en Suc. ${origen}: ${restante}${unidad}`;
  document.getElementById('tr-cantidad').max = Math.max(0, restante);
}

async function confirmarTraslado(){
  const msg = document.getElementById('tr-msg');
  if(!trProductoSel){ msg.className='scan-msg show'; msg.style.background='var(--red-bg)'; msg.style.color='var(--red)'; msg.textContent='Selecciona un producto'; return; }

  const origen = document.getElementById('tr-origen').value;
  const destino = document.getElementById('tr-destino').value;
  const cantidad = parseFloat(document.getElementById('tr-cantidad').value);

  if(origen === destino){ msg.className='scan-msg show'; msg.style.background='var(--red-bg)'; msg.style.color='var(--red)'; msg.textContent='La sucursal de origen y destino deben ser distintas'; return; }
  if(isNaN(cantidad) || cantidad<=0){ msg.className='scan-msg show'; msg.style.background='var(--red-bg)'; msg.style.color='var(--red)'; msg.textContent='Cantidad inválida'; return; }

  try{
    const r = await authFetch('/api/stock-sucursal/trasladar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({producto_id:trProductoSel.id, sucursal_origen:origen, sucursal_destino:destino, cantidad})
    });
    const d = await r.json();
    if(!r.ok){ msg.className='scan-msg show'; msg.style.background='var(--red-bg)'; msg.style.color='var(--red)'; msg.textContent=d.detail||'Error'; return; }
    toast(`✓ ${cantidad} trasladado de Suc.${origen} a Suc.${destino}`);
    cerrarTraslado();
    cargar();
  }catch(e){
    msg.className='scan-msg show'; msg.style.background='var(--red-bg)'; msg.style.color='var(--red)'; msg.textContent='Error de conexión';
  }
}

'''
    src = src.replace('cargar();', js_traslado + 'cargar();', 1)

    open(inv, 'w', encoding='utf-8').write(src)
    print("   ✓ Botón, modal y lógica de traslado agregados a inv_sucursales.html")
else:
    print("   • El botón de traslado ya existía")

print()
print("="*50)
print("✅ Todo listo. Reiniciando servicio...")
os.system("sudo systemctl restart inventario")
print("🚀 Refresca 'Inventario por sucursal' y el menú principal (Cmd+Shift+R).")
