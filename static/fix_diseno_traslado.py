#!/usr/bin/env python3
"""
Mejora el diseno del modal de Traslado de stock en Inventario por sucursal:
- Campos con estilo homologado (bordes, foco, radios) igual al resto de la app
- Resultados de busqueda como tarjetas en vez de texto plano
- Flecha visual entre sucursal origen/destino
- Boton de confirmar con el mismo estilo "primary" que el resto del sitio
- Estado de carga (deshabilitado) mientras se procesa el traslado
Uso: cd ~/inventario/static && python3 fix_diseno_traslado.py
"""
import os, re

INV = os.path.expanduser('~/inventario/static/inv_sucursales.html')
src = open(INV, encoding='utf-8').read()
original = src

cambios = 0

# ==== 1. Agregar CSS de diseno (solo si no existe ya) ======================
if 'tr-result-item' not in src:
    nuevo_css = '''
/* --- Diseno del modal de traslado --- */
.field{margin-bottom:14px}
.field label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px}
.field input,.field select{width:100%;height:42px;padding:0 12px;border:0.5px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);font-size:14px;font-family:inherit;transition:border-color .15s,box-shadow .15s}
.field input:focus,.field select:focus{outline:none;border-color:var(--blue);box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 18%,transparent)}
.tr-result-item{padding:10px 12px;border:0.5px solid var(--border);border-radius:10px;margin-bottom:6px;cursor:pointer;font-size:13px;background:var(--bg2);transition:background .12s,border-color .12s}
.tr-result-item:hover{background:var(--bg);border-color:var(--blue)}
.tr-selected-card{margin-top:8px;padding:.75rem .875rem;background:var(--blue-bg);border:0.5px solid color-mix(in srgb,var(--blue) 30%,transparent);border-radius:10px;font-size:13px;color:var(--blue);font-weight:600;align-items:center;gap:8px}
.tr-arrow-icon{text-align:center;font-size:20px;color:var(--text2);margin:-6px 0 12px}
.tr-empty{font-size:12px;color:var(--text2);padding:8px 2px}
.tr-hint{font-size:12px;color:var(--text2);margin-top:4px}
.modal-footer button:disabled{opacity:.5;cursor:not-allowed}
'''
    src = src.replace('</style>', nuevo_css + '</style>', 1)
    cambios += 1
    print("1. CSS de diseno agregado (campos, tarjetas, flecha, estados)")
else:
    print("1. El CSS ya estaba agregado, se omite")

# ==== 2. Reemplazar el modal completo por la version con mejor diseno ======
modal_viejo = re.search(
    r'<!-- Modal traslado de stock entre sucursales -->.*?(?=<!-- Modal escáner -->)',
    src, re.DOTALL
)

modal_nuevo = '''<!-- Modal traslado de stock entre sucursales -->
<div class="overlay" id="modal-traslado">
  <div class="modal">
    <h2>🔄 Trasladar stock entre sucursales</h2>
    <div class="field">
      <label>Producto</label>
      <input type="text" id="tr-buscar" placeholder="Buscar producto..." oninput="filtrarTraslado()" autocomplete="off">
      <div id="tr-resultados" style="margin-top:6px"></div>
      <div id="tr-seleccionado" class="tr-selected-card" style="display:none"></div>
    </div>
    <div class="field">
      <label>📤 De la sucursal</label>
      <select id="tr-origen" onchange="actualizarStockOrigen()"></select>
    </div>
    <div class="tr-arrow-icon">⬇</div>
    <div class="field">
      <label>📥 A la sucursal</label>
      <select id="tr-destino"></select>
    </div>
    <div class="field">
      <label>Cantidad a trasladar</label>
      <input type="number" id="tr-cantidad" min="0" step="1" placeholder="0">
      <div id="tr-disponible" class="tr-hint"></div>
    </div>
    <div class="scan-msg" id="tr-msg"></div>
    <div class="modal-footer">
      <button onclick="cerrarTraslado()">Cancelar</button>
      <button class="primary" id="tr-btn-confirmar" onclick="confirmarTraslado()">🔄 Confirmar traslado</button>
    </div>
  </div>
</div>

'''

if modal_viejo:
    src = src[:modal_viejo.start()] + modal_nuevo + src[modal_viejo.end():]
    cambios += 1
    print("2. Modal de traslado rediseñado (campos, flecha, boton primario)")
else:
    print("2. No se encontro el modal viejo (puede que ya este actualizado)")

# ==== 3. Resultados de busqueda: tarjetas en vez de texto plano ============
patron_filtrar = re.compile(
    r"cont\.innerHTML = encontrados\.map\(p=>`.*?`\)\.join\(''\);",
    re.DOTALL
)
nuevo_filtrar = (
    "cont.innerHTML = encontrados.map(p=>`\n"
    "    <div class=\"tr-result-item\" onclick='seleccionarProductoTraslado(${p.id})'>\n"
    "      <strong>${esc(p.nombre)}</strong>${p.marca?' · '+esc(p.marca):''}\n"
    "    </div>`).join('');"
)
if patron_filtrar.search(src):
    src = patron_filtrar.sub(nuevo_filtrar, src, count=1)
    cambios += 1
    print("3. Resultados de busqueda ahora son tarjetas con hover")

# Mensaje "Sin resultados" con clase en vez de estilo inline
src = src.replace(
    "cont.innerHTML = '<div style=\"font-size:12px;color:var(--text2);padding:6px 0\">Sin resultados</div>'; return;",
    "cont.innerHTML = '<div class=\"tr-empty\">Sin resultados</div>'; return;"
)

# ==== 4. display 'block' -> 'flex' para la tarjeta de producto seleccionado
if "sel.style.display = 'block';" in src:
    src = src.replace("sel.style.display = 'block';", "sel.style.display = 'flex';")
    cambios += 1
    print("4. Tarjeta de producto seleccionado usa flex (icono + nombre alineados)")

# ==== 5. Boton de confirmar con estado de carga (deshabilitado mientras procesa)
patron_confirmar = re.compile(
    r"async function confirmarTraslado\(\)\{.*?\n\}",
    re.DOTALL
)
nuevo_confirmar = '''async function confirmarTraslado(){
  const msg = document.getElementById('tr-msg');
  const btn = document.getElementById('tr-btn-confirmar');

  function mostrarError(texto){
    msg.className='scan-msg show'; msg.style.background='var(--red-bg)'; msg.style.color='var(--red)'; msg.textContent=texto;
  }

  if(!trProductoSel){ mostrarError('Selecciona un producto'); return; }

  const origen = document.getElementById('tr-origen').value;
  const destino = document.getElementById('tr-destino').value;
  const cantidad = parseFloat(document.getElementById('tr-cantidad').value);

  if(origen === destino){ mostrarError('La sucursal de origen y destino deben ser distintas'); return; }
  if(isNaN(cantidad) || cantidad<=0){ mostrarError('Cantidad inválida'); return; }

  const textoOriginal = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Trasladando...';

  try{
    const r = await authFetch('/api/stock-sucursal/trasladar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({producto_id:trProductoSel.id, sucursal_origen:origen, sucursal_destino:destino, cantidad})
    });
    const d = await r.json();
    if(!r.ok){ mostrarError(d.detail||'Error'); btn.disabled=false; btn.textContent=textoOriginal; return; }
    toast(`✓ ${cantidad} trasladado de Suc.${origen} a Suc.${destino}`);
    cerrarTraslado();
    cargar();
  }catch(e){
    mostrarError('Error de conexión');
    btn.disabled = false;
    btn.textContent = textoOriginal;
  }
}'''
if patron_confirmar.search(src):
    src = patron_confirmar.sub(nuevo_confirmar, src, count=1)
    cambios += 1
    print("5. Boton de confirmar ahora muestra 'Trasladando...' mientras procesa")

# ==== 6. Resetear el boton de confirmar cada vez que se abre el modal =====
if "document.getElementById('modal-traslado').classList.add('open');\n  actualizarStockOrigen();" in src \
   and "tr-btn-confirmar').disabled=false" not in src:
    src = src.replace(
        "document.getElementById('modal-traslado').classList.add('open');\n  actualizarStockOrigen();",
        "const _btnR = document.getElementById('tr-btn-confirmar');\n"
        "  if(_btnR){ _btnR.disabled=false; _btnR.textContent='🔄 Confirmar traslado'; }\n"
        "  document.getElementById('modal-traslado').classList.add('open');\n"
        "  actualizarStockOrigen();"
    )
    cambios += 1
    print("6. El boton se reinicia correctamente cada vez que se abre el modal")

# ==== Guardar y verificar =====
if src != original:
    open(INV, 'w', encoding='utf-8').write(src)
    print("")
    print("Archivo guardado con " + str(cambios) + " mejora(s) de diseno")
else:
    print("")
    print("No se aplico ningun cambio (el archivo ya podria estar actualizado)")

# Verificacion basica de balance de llaves en los <script>
scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
print("")
print("Verificando balance de llaves en <script>...")
ok = True
for i, s in enumerate(scripts):
    o, c = s.count('{'), s.count('}')
    estado = 'OK' if o == c else 'DESBALANCEADO'
    if o != c: ok = False
    print("  Script " + str(i+1) + ": {" + str(o) + " }" + str(c) + " " + estado)

if ok:
    print("")
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Refresca 'Inventario por sucursal' (Cmd+Shift+R).")
else:
    print("")
    print("ADVERTENCIA: hay un desbalance de llaves. NO se reinicio el servicio.")
    print("Comparte este resultado para revisarlo antes de reiniciar.")
