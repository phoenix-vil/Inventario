// Helpers de sesión compartidos por todas las páginas
function getSesion() {
  try { return JSON.parse(localStorage.getItem('sesion') || 'null'); }
  catch (e) { return null; }
}

function requireAuth() {
  const s = getSesion();
  if (!s || !s.token) { location.href = '/login'; return null; }
  return s;
}

function requireGerente() {
  const s = requireAuth();
  if (s && s.rol !== 'gerente') { location.href = '/'; return null; }
  return s;
}

function esGerente() {
  const s = getSesion();
  return s && s.rol === 'gerente';
}

async function logout() {
  const s = getSesion();
  if (s && s.token) {
    try {
      await fetch('/api/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: s.token })
      });
    } catch (e) {}
  }
  localStorage.removeItem('sesion');
  location.href = '/login';
}

// fetch con el token de sesión; redirige a login si el token caduca
// Si skipAuthRedirect=true, un 401 no cierra la sesión (úsalo en endpoints
// que validan OTRAS credenciales, como /api/pos/autorizar)
async function authFetch(url, opts = {}, skipAuthRedirect = false) {
  const s = getSesion();
  opts.headers = opts.headers || {};
  if (s && s.token) opts.headers['Authorization'] = 'Bearer ' + s.token;
  const r = await fetch(url, opts);
  if (r.status === 401 && !skipAuthRedirect) {
    localStorage.removeItem('sesion');
    location.href = '/login';
  }
  return r;
}

// ─── Chequeo periodico de sesion + auto-actualizacion ──────────────────────
// Cada 20 minutos: valida que la sesion siga activa (si expiro, manda a login)
// y recarga la pagina para traer actualizaciones, salvo que haya un modal
// abierto o un carrito de venta con productos (para no interrumpir al usuario).
(function () {
  const INTERVALO_MIN = 20;
  setInterval(async () => {
    const s = getSesion();
    if (!s || !s.token) return;

    try {
      const r = await fetch('/api/sesion', { headers: { 'Authorization': 'Bearer ' + s.token } });
      if (r.status === 401) {
        localStorage.removeItem('sesion');
        location.href = '/login';
        return;
      }
    } catch (e) {
      return; // sin conexion por ahora, se reintenta en el siguiente ciclo
    }

    if (document.querySelector('.overlay.open')) return;
    if (typeof carrito !== 'undefined' && Array.isArray(carrito) && carrito.length > 0) return;

    location.reload();
  }, INTERVALO_MIN * 60 * 1000);
})();

// ─── Modales genericos (reemplazan confirm()/prompt() nativos, poco ─────────
// ─── confiables en iOS standalone). Se inyectan solos en cualquier pagina. ──
function _inyectarModalesGenericos(){
  if(document.getElementById('confirmar-generico-modal')) return;
  const div = document.createElement('div');
  div.innerHTML = `
    <div id="confirmar-generico-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);align-items:center;justify-content:center;z-index:9999;padding:1rem">
      <div style="background:var(--bg2,#252522);border:0.5px solid var(--border,#3a3a36);border-radius:16px;padding:1.5rem;width:340px;max-width:96vw">
        <h2 id="confirmar-generico-titulo" style="font-size:17px;font-weight:600;margin-bottom:12px;color:var(--text,#e8e6dc)">¿Confirmar?</h2>
        <p id="confirmar-generico-mensaje" style="font-size:14px;color:var(--text2,#9c9a92);margin-bottom:1.25rem;white-space:pre-line"></p>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <button onclick="_resolverConfirmarGenerico(false)" style="height:42px;padding:0 16px;border-radius:9px;border:0.5px solid var(--border,#3a3a36);background:transparent;color:var(--text,#e8e6dc);cursor:pointer;font-size:14px">Cancelar</button>
          <button onclick="_resolverConfirmarGenerico(true)" style="height:42px;padding:0 16px;border-radius:9px;border:none;background:var(--text,#e8e6dc);color:var(--bg,#1c1c1a);font-weight:600;cursor:pointer;font-size:14px">Continuar</button>
        </div>
      </div>
    </div>
    <div id="prompt-generico-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);align-items:center;justify-content:center;z-index:9999;padding:1rem">
      <div style="background:var(--bg2,#252522);border:0.5px solid var(--border,#3a3a36);border-radius:16px;padding:1.5rem;width:340px;max-width:96vw">
        <h2 id="prompt-generico-titulo" style="font-size:17px;font-weight:600;margin-bottom:12px;color:var(--text,#e8e6dc)">Escribe un valor</h2>
        <p id="prompt-generico-mensaje" style="font-size:13px;color:var(--text2,#9c9a92);margin-bottom:12px"></p>
        <input type="text" id="prompt-generico-input" autocomplete="off" style="width:100%;height:44px;padding:0 14px;border:0.5px solid var(--border,#3a3a36);border-radius:10px;background:var(--bg,#1c1c1a);color:var(--text,#e8e6dc);font-size:15px;box-sizing:border-box;margin-bottom:16px">
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <button onclick="_cancelarPromptGenerico()" style="height:42px;padding:0 16px;border-radius:9px;border:0.5px solid var(--border,#3a3a36);background:transparent;color:var(--text,#e8e6dc);cursor:pointer;font-size:14px">Cancelar</button>
          <button onclick="_aceptarPromptGenerico()" style="height:42px;padding:0 16px;border-radius:9px;border:none;background:var(--text,#e8e6dc);color:var(--bg,#1c1c1a);font-weight:600;cursor:pointer;font-size:14px">Aceptar</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(div);
}

let _resolverConfirmarGenericoFn = null;
function confirmarPersonalizado(mensaje, titulo){
  _inyectarModalesGenericos();
  return new Promise((resolve)=>{
    document.getElementById('confirmar-generico-titulo').textContent = titulo || '¿Confirmar?';
    document.getElementById('confirmar-generico-mensaje').textContent = mensaje;
    document.getElementById('confirmar-generico-modal').style.display = 'flex';
    _resolverConfirmarGenericoFn = (valor)=>{
      document.getElementById('confirmar-generico-modal').style.display = 'none';
      _resolverConfirmarGenericoFn = null;
      resolve(valor);
    };
  });
}
function _resolverConfirmarGenerico(valor){
  if(_resolverConfirmarGenericoFn) _resolverConfirmarGenericoFn(valor);
}

let _resolverPromptFn = null;
function promptPersonalizado(mensaje, valorDefault, titulo){
  _inyectarModalesGenericos();
  return new Promise((resolve)=>{
    document.getElementById('prompt-generico-titulo').textContent = titulo || 'Escribe un valor';
    document.getElementById('prompt-generico-mensaje').textContent = mensaje || '';
    const input = document.getElementById('prompt-generico-input');
    input.value = valorDefault || '';
    document.getElementById('prompt-generico-modal').style.display = 'flex';
    setTimeout(()=>input.focus(), 60);
    _resolverPromptFn = (valor)=>{
      document.getElementById('prompt-generico-modal').style.display = 'none';
      _resolverPromptFn = null;
      resolve(valor);
    };
  });
}
function _cancelarPromptGenerico(){
  if(_resolverPromptFn) _resolverPromptFn(null);
}
function _aceptarPromptGenerico(){
  const valor = document.getElementById('prompt-generico-input').value;
  if(_resolverPromptFn) _resolverPromptFn(valor);
}
