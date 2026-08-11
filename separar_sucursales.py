#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Separa Sucursales en su propia pagina independiente:
1. Crea static/sucursales.html (nueva).
2. Quita la seccion de Sucursales de usuarios.html (HTML + JS).
3. Agrega la ruta /sucursales en main.py.
4. Actualiza el enlace del menu de Configuracion.
Uso: cd ~/inventario && python3 separar_sucursales.py
"""
import os, re

BASE = os.path.expanduser('~/inventario')
STATIC = os.path.join(BASE, 'static')

SUCURSALES_HTML_B64 = 'PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImVzIj4KPGhlYWQ+CjxtZXRhIGNoYXJzZXQ9IlVURi04Ij4KPGxpbmsgcmVsPSJpY29uIiB0eXBlPSJpbWFnZS9wbmciIGhyZWY9Ii9zdGF0aWMvaWNvbi1zcXVhcmUucG5nP3Y9MTc4MzUzODI4OSI+CjxsaW5rIHJlbD0iYXBwbGUtdG91Y2gtaWNvbiIgaHJlZj0iL3N0YXRpYy9pY29uLXNxdWFyZS5wbmc/dj0xNzgzNTM4Mjg5Ij4KPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwgaW5pdGlhbC1zY2FsZT0xLjAiPgo8dGl0bGU+U3VjdXJzYWxlcyDCtyBPbmx5IEVudGVycHJpc2VzPC90aXRsZT4KPHN0eWxlPgoqe2JveC1zaXppbmc6Ym9yZGVyLWJveDttYXJnaW46MDtwYWRkaW5nOjB9Cjpyb290ewogIC0tYmc6I2Y1ZjRmMDstLWJnMjojZmZmOy0tYm9yZGVyOiNlMmUwZDg7LS10ZXh0OiMxYTFhMTg7LS10ZXh0MjojNmI2YjY2OwogIC0tYmx1ZTojMTg1ZmE1Oy0tYmx1ZS1iZzojZTZmMWZiOy0tZ3JlZW46IzNiNmQxMTstLWdyZWVuLWJnOiNlYWYzZGU7CiAgLS1yZWQ6I2EzMmQyZDstLXJlZC1iZzojZmNlYmViOy0tcmFkaXVzOjEwcHgKfQpAbWVkaWEocHJlZmVycy1jb2xvci1zY2hlbWU6ZGFyayl7OnJvb3R7CiAgLS1iZzojMWMxYzFhOy0tYmcyOiMyNTI1MjI7LS1ib3JkZXI6IzNhM2EzNjstLXRleHQ6I2U4ZTZkYzstLXRleHQyOiM5YzlhOTI7CiAgLS1ibHVlOiM4NWI3ZWI7LS1ibHVlLWJnOiMwNDJjNTM7LS1ncmVlbjojOTdjNDU5Oy0tZ3JlZW4tYmc6IzE3MzQwNDsKICAtLXJlZDojZjA5NTk1Oy0tcmVkLWJnOiM1MDEzMTMKfX0KYm9keXtmb250LWZhbWlseTotYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnU2Vnb2UgVUknLHNhbnMtc2VyaWY7YmFja2dyb3VuZDp2YXIoLS1iZyk7Y29sb3I6dmFyKC0tdGV4dCk7bWluLWhlaWdodDoxMDB2aH0KLnRvcGJhcntiYWNrZ3JvdW5kOnZhcigtLWJnMik7Ym9yZGVyLWJvdHRvbTowLjVweCBzb2xpZCB2YXIoLS1ib3JkZXIpO3BhZGRpbmc6MCAxcmVtO2hlaWdodDo1NHB4O2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjEwcHg7cG9zaXRpb246c3RpY2t5O3RvcDowO3otaW5kZXg6MTB9Ci50b3BiYXItdGl0bGV7Zm9udC1zaXplOjE3cHg7Zm9udC13ZWlnaHQ6NjAwO2ZsZXg6MTt0ZXh0LWFsaWduOmNlbnRlcjt3aGl0ZS1zcGFjZTpub3dyYXA7b3ZlcmZsb3c6aGlkZGVuO3RleHQtb3ZlcmZsb3c6ZWxsaXBzaXN9Ci50b3BiYXItcmlnaHR7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtmbGV4LXNocmluazowO21pbi13aWR0aDo4NHB4O2p1c3RpZnktY29udGVudDpmbGV4LWVuZH0KLmJ0bi1pbmljaW97ZGlzcGxheTppbmxpbmUtZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjVweDtoZWlnaHQ6MzZweDtwYWRkaW5nOjAgMTJweDtib3JkZXI6MC41cHggc29saWQgdmFyKC0tYm9yZGVyKTtib3JkZXItcmFkaXVzOjhweDtiYWNrZ3JvdW5kOnRyYW5zcGFyZW50O2NvbG9yOnZhcigtLXRleHQpO2ZvbnQtc2l6ZToxM3B4O3RleHQtZGVjb3JhdGlvbjpub25lO2ZsZXgtc2hyaW5rOjA7d2hpdGUtc3BhY2U6bm93cmFwfQouYnRuLWluaWNpbzpob3ZlcntiYWNrZ3JvdW5kOnZhcigtLWJnKX0KLmNvbnRhaW5lcnttYXgtd2lkdGg6NjAwcHg7bWFyZ2luOjAgYXV0bztwYWRkaW5nOjEuMjVyZW19Ci5zZWN0aW9uLXRpdGxle2ZvbnQtc2l6ZToxM3B4O2ZvbnQtd2VpZ2h0OjYwMDtjb2xvcjp2YXIoLS10ZXh0Mik7bWFyZ2luOjEuNXJlbSAwIC43NXJlbTt0ZXh0LXRyYW5zZm9ybTp1cHBlcmNhc2U7bGV0dGVyLXNwYWNpbmc6LjVweH0KLnNlY3Rpb24tdGl0bGU6Zmlyc3QtY2hpbGR7bWFyZ2luLXRvcDowfQouY2FyZHtiYWNrZ3JvdW5kOnZhcigtLWJnMik7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czoxMnB4O292ZXJmbG93OmhpZGRlbn0KLnVzZXItcm93e2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjEwcHg7cGFkZGluZzouODc1cmVtIDFyZW07Ym9yZGVyLWJvdHRvbTowLjVweCBzb2xpZCB2YXIoLS1ib3JkZXIpfQoudXNlci1yb3c6bGFzdC1jaGlsZHtib3JkZXItYm90dG9tOm5vbmV9Ci51LWluZm97ZmxleDoxO21pbi13aWR0aDowfQoudS1uYW1le2ZvbnQtd2VpZ2h0OjYwMDtmb250LXNpemU6MTRweH0KLnUtYWN0aW9uc3tkaXNwbGF5OmZsZXg7Z2FwOjZweH0KLnUtYWN0aW9ucyBidXR0b257aGVpZ2h0OjMycHg7cGFkZGluZzowIDEwcHg7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czo3cHg7YmFja2dyb3VuZDp0cmFuc3BhcmVudDtjb2xvcjp2YXIoLS10ZXh0KTtmb250LXNpemU6MTJweDtjdXJzb3I6cG9pbnRlcn0KLnUtYWN0aW9ucyBidXR0b24uZGFuZ2Vye2NvbG9yOnZhcigtLXJlZCk7Ym9yZGVyLWNvbG9yOnRyYW5zcGFyZW50O2JhY2tncm91bmQ6dmFyKC0tcmVkLWJnKX0KLmZvcm0tY2FyZHtiYWNrZ3JvdW5kOnZhcigtLWJnMik7Ym9yZGVyOjAuNXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czoxMnB4O3BhZGRpbmc6MS4yNXJlbX0KLmZpZWxke21hcmdpbi1ib3R0b206MTJweH0KLmZpZWxkIGxhYmVse2Rpc3BsYXk6YmxvY2s7Zm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tdGV4dDIpO21hcmdpbi1ib3R0b206NHB4fQouZmllbGQgaW5wdXR7d2lkdGg6MTAwJTtoZWlnaHQ6NDJweDtwYWRkaW5nOjAgMTJweDtib3JkZXI6MC41cHggc29saWQgdmFyKC0tYm9yZGVyKTtib3JkZXItcmFkaXVzOjhweDtiYWNrZ3JvdW5kOnZhcigtLWJnKTtjb2xvcjp2YXIoLS10ZXh0KTtmb250LXNpemU6MTZweDtmb250LWZhbWlseTppbmhlcml0fQouYnRue3dpZHRoOjEwMCU7aGVpZ2h0OjQ2cHg7Ym9yZGVyOm5vbmU7Ym9yZGVyLXJhZGl1czoxMHB4O2JhY2tncm91bmQ6dmFyKC0tdGV4dCk7Y29sb3I6dmFyKC0tYmcyKTtmb250LXNpemU6MTVweDtmb250LXdlaWdodDo2MDA7Y3Vyc29yOnBvaW50ZXI7bWFyZ2luLXRvcDo0cHh9Ci5tc2d7cGFkZGluZzoxMHB4O2JvcmRlci1yYWRpdXM6OHB4O2ZvbnQtc2l6ZToxM3B4O21hcmdpbi10b3A6MTBweDtkaXNwbGF5Om5vbmV9Ci5tc2cuc2hvd3tkaXNwbGF5OmJsb2NrfQoubXNnLmVycm9ye2JhY2tncm91bmQ6dmFyKC0tcmVkLWJnKTtjb2xvcjp2YXIoLS1yZWQpfQoubXNnLm9re2JhY2tncm91bmQ6dmFyKC0tZ3JlZW4tYmcpO2NvbG9yOnZhcigtLWdyZWVuKX0KQG1lZGlhKG1heC13aWR0aDo1NjBweCl7LnRvcGJhcntwYWRkaW5nOjAgLjYyNXJlbX0udG9wYmFyLXRpdGxle2ZvbnQtc2l6ZToxNXB4fS50b3BiYXItcmlnaHR7bWluLXdpZHRoOjB9LmNvbnRhaW5lcntwYWRkaW5nOi44NzVyZW19fQo8L3N0eWxlPgo8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Ii9zdGF0aWMvbW9kZXJuLmNzcyI+CjwvaGVhZD4KPGJvZHk+Cgo8ZGl2IGNsYXNzPSJ0b3BiYXIiPgogIDxhIGhyZWY9Ii8iIGNsYXNzPSJidG4taW5pY2lvIiB0aXRsZT0iSW5pY2lvIj48aW1nIHNyYz0iL3N0YXRpYy9pY29uLW5hdi12Mi5wbmciIGFsdD0iSW5pY2lvIiBjbGFzcz0ibmF2LWljb24iIHN0eWxlPSJoZWlnaHQ6MzJweDt3aWR0aDozMnB4Ij48L2E+CiAgPGgxIGNsYXNzPSJ0b3BiYXItdGl0bGUiPvCfj6ogU3VjdXJzYWxlczwvaDE+CiAgPGRpdiBjbGFzcz0idG9wYmFyLXJpZ2h0Ij48L2Rpdj4KPC9kaXY+Cgo8ZGl2IGNsYXNzPSJjb250YWluZXIiPgogIDxkaXYgY2xhc3M9InNlY3Rpb24tdGl0bGUiPlN1Y3Vyc2FsZXMgcmVnaXN0cmFkYXM8L2Rpdj4KICA8ZGl2IGNsYXNzPSJjYXJkIiBpZD0ibGlzdGEtc3VjdXJzYWxlcyI+PC9kaXY+CgogIDxkaXYgY2xhc3M9InNlY3Rpb24tdGl0bGUiPkFncmVnYXIgc3VjdXJzYWw8L2Rpdj4KICA8ZGl2IGNsYXNzPSJmb3JtLWNhcmQiPgogICAgPGRpdiBjbGFzcz0iZmllbGQiPjxsYWJlbD5Ob21icmUgLyBuw7ptZXJvIGRlIHN1Y3Vyc2FsPC9sYWJlbD48aW5wdXQgaWQ9Im5zLW5vbWJyZSIgcGxhY2Vob2xkZXI9IkVqOiAyLCBDZW50cm8sIE5vcnRlLi4uIiBhdXRvY29tcGxldGU9Im9mZiI+PC9kaXY+CiAgICA8YnV0dG9uIGNsYXNzPSJidG4iIG9uY2xpY2s9ImNyZWFyU3VjdXJzYWwoKSI+QWdyZWdhciBzdWN1cnNhbDwvYnV0dG9uPgogICAgPGRpdiBjbGFzcz0ibXNnIiBpZD0ic3VjdXJzYWwtbXNnIj48L2Rpdj4KICA8L2Rpdj4KPC9kaXY+Cgo8c2NyaXB0IHNyYz0iL3N0YXRpYy9hdXRoLmpzIj48L3NjcmlwdD4KPHNjcmlwdD4KcmVxdWlyZUdlcmVudGUoKTsKCmZ1bmN0aW9uIGVzYyhzKXtyZXR1cm4gU3RyaW5nKHMpLnJlcGxhY2UoLyYvZywnJmFtcDsnKS5yZXBsYWNlKC88L2csJyZsdDsnKS5yZXBsYWNlKC8+L2csJyZndDsnKTt9Cgphc3luYyBmdW5jdGlvbiBjYXJnYXJTdWN1cnNhbGVzKCl7CiAgdHJ5ewogICAgY29uc3QgciA9IGF3YWl0IGZldGNoKCcvYXBpL3N1Y3Vyc2FsZXMnKTsKICAgIGNvbnN0IHN1Y3Vyc2FsZXMgPSBhd2FpdCByLmpzb24oKTsKICAgIGNvbnN0IGNvbnQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbGlzdGEtc3VjdXJzYWxlcycpOwogICAgaWYoIXN1Y3Vyc2FsZXMubGVuZ3RoKXtjb250LmlubmVySFRNTD0nPGRpdiBjbGFzcz0idXNlci1yb3ciPjxkaXYgY2xhc3M9InUtaW5mbyI+U2luIHN1Y3Vyc2FsZXMgcmVnaXN0cmFkYXM8L2Rpdj48L2Rpdj4nO3JldHVybjt9CiAgICBjb250LmlubmVySFRNTCA9IHN1Y3Vyc2FsZXMubWFwKHM9PmA8ZGl2IGNsYXNzPSJ1c2VyLXJvdyI+CiAgICAgIDxkaXYgY2xhc3M9InUtaW5mbyI+PGRpdiBjbGFzcz0idS1uYW1lIj4ke2VzYyhzLm5vbWJyZSl9PC9kaXY+PC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9InUtYWN0aW9ucyI+PGJ1dHRvbiBjbGFzcz0iZGFuZ2VyIiBvbmNsaWNrPSJib3JyYXJTdWN1cnNhbCgke3MuaWR9LCcke2VzYyhzLm5vbWJyZSl9JykiPvCfl5E8L2J1dHRvbj48L2Rpdj4KICAgIDwvZGl2PmApLmpvaW4oJycpOwogIH1jYXRjaChlKXt9Cn0KCmFzeW5jIGZ1bmN0aW9uIGNyZWFyU3VjdXJzYWwoKXsKICBjb25zdCBtc2cgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3VjdXJzYWwtbXNnJyk7CiAgY29uc3Qgbm9tYnJlID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ25zLW5vbWJyZScpLnZhbHVlLnRyaW0oKTsKICBpZighbm9tYnJlKXttc2cuY2xhc3NOYW1lPSdtc2cgZXJyb3Igc2hvdyc7bXNnLnRleHRDb250ZW50PSdFc2NyaWJlIHVuIG5vbWJyZSBwYXJhIGxhIHN1Y3Vyc2FsJztyZXR1cm47fQogIHRyeXsKICAgIGNvbnN0IHIgPSBhd2FpdCBhdXRoRmV0Y2goJy9hcGkvc3VjdXJzYWxlcycse21ldGhvZDonUE9TVCcsaGVhZGVyczp7J0NvbnRlbnQtVHlwZSc6J2FwcGxpY2F0aW9uL2pzb24nfSxib2R5OkpTT04uc3RyaW5naWZ5KHtub21icmV9KX0pOwogICAgY29uc3QgZGF0YSA9IGF3YWl0IHIuanNvbigpOwogICAgaWYoIXIub2spe21zZy5jbGFzc05hbWU9J21zZyBlcnJvciBzaG93Jzttc2cudGV4dENvbnRlbnQ9ZGF0YS5kZXRhaWx8fCdFcnJvcic7cmV0dXJuO30KICAgIG1zZy5jbGFzc05hbWU9J21zZyBvayBzaG93Jzttc2cudGV4dENvbnRlbnQ9YFN1Y3Vyc2FsICIke2RhdGEubm9tYnJlfSIgYWdyZWdhZGEuYDsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCducy1ub21icmUnKS52YWx1ZT0nJzsKICAgIGNhcmdhclN1Y3Vyc2FsZXMoKTsKICB9Y2F0Y2goZSl7bXNnLmNsYXNzTmFtZT0nbXNnIGVycm9yIHNob3cnO21zZy50ZXh0Q29udGVudD0nRXJyb3IgZGUgY29uZXhpw7NuJzt9Cn0KCmFzeW5jIGZ1bmN0aW9uIGJvcnJhclN1Y3Vyc2FsKGlkLG5vbWJyZSl7CiAgaWYoIWNvbmZpcm0oYMK/RWxpbWluYXIgbGEgc3VjdXJzYWwgIiR7bm9tYnJlfSI/YCkpcmV0dXJuOwogIHRyeXsKICAgIGNvbnN0IHIgPSBhd2FpdCBhdXRoRmV0Y2goJy9hcGkvc3VjdXJzYWxlcy8nK2lkLHttZXRob2Q6J0RFTEVURSd9KTsKICAgIGlmKHIuc3RhdHVzPT09MjA0KXtjYXJnYXJTdWN1cnNhbGVzKCk7cmV0dXJuO30KICAgIGNvbnN0IGRhdGEgPSBhd2FpdCByLmpzb24oKTsKICAgIGFsZXJ0KGRhdGEuZGV0YWlsfHwnTm8gc2UgcHVkbyBlbGltaW5hcicpOwogIH1jYXRjaChlKXthbGVydCgnRXJyb3IgZGUgY29uZXhpw7NuJyk7fQp9CgpjYXJnYXJTdWN1cnNhbGVzKCk7Cjwvc2NyaXB0Pgo8L2JvZHk+CjwvaHRtbD4K'
import base64

# ================================================================
# 1. Crear static/sucursales.html
# ================================================================
print("1. Creando static/sucursales.html...")
suc_path = os.path.join(STATIC, 'sucursales.html')
with open(suc_path, 'wb') as f:
    f.write(base64.b64decode(SUCURSALES_HTML_B64))
print("   OK sucursales.html creado (" + str(os.path.getsize(suc_path)) + " bytes)")

# ================================================================
# 2. Quitar la seccion de Sucursales de usuarios.html
# ================================================================
print("2. Limpiando usuarios.html (quitando Sucursales)...")
usu_path = os.path.join(STATIC, 'usuarios.html')
src = open(usu_path, encoding='utf-8').read()
original = src

# --- Quitar el bloque HTML ---
viejo_html = '''  <div class="section-title" id="sucursales">Sucursales</div>
  <div class="card" id="lista-sucursales"></div>

  <div class="section-title">Agregar sucursal</div>
  <div class="form-card">
    <div class="field"><label>Nombre / número de sucursal</label><input id="ns-nombre" placeholder="Ej: 2, Centro, Norte..." autocomplete="off"></div>
    <button class="btn" onclick="crearSucursal()">Agregar sucursal</button>
    <div class="msg" id="sucursal-msg"></div>
  </div>
'''
n1 = src.count(viejo_html)
if n1 == 1:
    src = src.replace(viejo_html, '', 1)
    print("   OK bloque HTML de Sucursales eliminado")
elif 'id="sucursales"' not in src:
    print("   * Ya estaba quitado")
else:
    print("   ERROR: no se encontro el bloque HTML exacto")

# --- Quitar el bloque JS ---
viejo_js = '''
// ─── Sucursales ──────────────────────────────────────────────────────────
async function cargarSucursales(){
  try{
    const r = await fetch('/api/sucursales');
    const sucursales = await r.json();
    const cont = document.getElementById('lista-sucursales');
    if(!sucursales.length){cont.innerHTML='<div class="user-row"><div class="u-info">Sin sucursales registradas</div></div>';return;}
    cont.innerHTML = sucursales.map(s=>`<div class="user-row">
      <div class="u-info"><div class="u-name">${esc(s.nombre)}</div></div>
      <div class="u-actions"><button class="danger" onclick="borrarSucursal(${s.id},'${esc(s.nombre)}')">🗑</button></div>
    </div>`).join('');
  }catch(e){}
}

async function crearSucursal(){
  const msg = document.getElementById('sucursal-msg');
  const nombre = document.getElementById('ns-nombre').value.trim();
  if(!nombre){msg.className='msg error show';msg.textContent='Escribe un nombre para la sucursal';return;}
  try{
    const r = await authFetch('/api/sucursales',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre})});
    const data = await r.json();
    if(!r.ok){msg.className='msg error show';msg.textContent=data.detail||'Error';return;}
    msg.className='msg ok show';msg.textContent=`Sucursal "${data.nombre}" agregada.`;
    document.getElementById('ns-nombre').value='';
    cargarSucursales();
  }catch(e){msg.className='msg error show';msg.textContent='Error de conexión';}
}

async function borrarSucursal(id,nombre){
  if(!confirm(`¿Eliminar la sucursal "${nombre}"?`))return;
  try{
    const r = await authFetch('/api/sucursales/'+id,{method:'DELETE'});
    if(r.status===204){cargarSucursales();return;}
    const data = await r.json();
    alert(data.detail||'No se pudo eliminar');
  }catch(e){alert('Error de conexión');}
}
'''
n2 = src.count(viejo_js)
if n2 == 1:
    src = src.replace(viejo_js, '', 1)
    print("   OK funciones JS de Sucursales eliminadas")
elif 'function crearSucursal' not in src:
    print("   * Ya estaba quitado")
else:
    print("   ERROR: no se encontro el bloque JS exacto")

# --- Quitar la llamada final a cargarSucursales() ---
viejo_final = '''cargar();
cargarSucursales();'''
nuevo_final = 'cargar();'
n3 = src.count(viejo_final)
if n3 == 1:
    src = src.replace(viejo_final, nuevo_final, 1)
    print("   OK llamada final ajustada")

if src != original:
    open(usu_path, 'w', encoding='utf-8').write(src)
    print("   usuarios.html guardado.")

# ================================================================
# 3. main.py: agregar la ruta /sucursales
# ================================================================
print("3. Agregando ruta /sucursales a main.py...")
main_path = os.path.join(BASE, 'main.py')
msrc = open(main_path, encoding='utf-8').read()

if '"/sucursales"' not in msrc and "'/sucursales'" not in msrc:
    ruta = '''

@app.get("/sucursales", response_class=FileResponse)
def sucursales_page():
    return FileResponse("static/sucursales.html")
'''
    msrc = msrc.rstrip('\n') + ruta + '\n'
    open(main_path, 'w', encoding='utf-8').write(msrc)
    print("   OK ruta /sucursales agregada")
else:
    print("   * Ya existia")

import ast
try:
    ast.parse(open(main_path, encoding='utf-8').read())
    print("   Sintaxis de main.py: OK")
    main_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis: linea " + str(e.lineno) + ": " + str(e.text))
    main_ok = False

# ================================================================
# 4. menu.html: cambiar el enlace de Sucursales
# ================================================================
print("4. Actualizando enlace de Sucursales en el menu...")
menu_path = os.path.join(STATIC, 'menu.html')
menu_src = open(menu_path, encoding='utf-8').read()

viejo_link = 'href="/usuarios#sucursales"'
nuevo_link = 'href="/sucursales"'
n4 = menu_src.count(viejo_link)
if n4 == 1:
    menu_src = menu_src.replace(viejo_link, nuevo_link, 1)
    open(menu_path, 'w', encoding='utf-8').write(menu_src)
    print("   OK enlace actualizado a /sucursales")
elif 'href="/sucursales"' in menu_src:
    print("   * Ya estaba actualizado")
else:
    print("   ERROR: no se encontro el enlace exacto")

# ================================================================
# Verificar y reiniciar
# ================================================================
scripts_usu = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok_usu = all(s.count('{') == s.count('}') for s in scripts_usu)

print()
print("Balance de llaves en usuarios.html:", "OK" if ok_usu else "DESBALANCEADO")

print()
print("=" * 55)
if main_ok and ok_usu:
    print("Todo en orden. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. /usuarios y /sucursales ahora son paginas independientes.")
else:
    print("ADVERTENCIA: revisar los errores de arriba. NO se reinicio el servicio.")
