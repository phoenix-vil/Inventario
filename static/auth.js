// Helpers de sesión compartidos por todas las páginas
function getSesion() {
  try { return JSON.parse(localStorage.getItem('sesion') || 'null'); }
  catch (e) { return null; }
}

function requireAuth() {
  const s = getSesion();
  if (!s || !s.token) { location.href = '/login'; return null; }
  aplicarTemaTienda();
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

// Para las pantallas que administran la empresa entera (inventario por
// sucursal, alta de sucursales, clasificación por tienda). El backend las
// protege con requerir_enterprise; esto solo evita que una sesión de sucursal
// que llegue por URL se quede viendo una pantalla que no le va a cargar.
function requireEnterprise() {
  const s = requireGerente();
  if (s && !sesionVeTodo()) { location.href = '/'; return null; }
  return s;
}

// Para las pantallas de piso (vender, devolver, cancelar) que Only Enterprises
// no debe usar: no es una sucursal, no tiene caja ni inventario propio que
// vender. El backend las protege con requerir_sucursal_operativa(); esto solo
// evita que la sesión se quede viendo una pantalla que al confirmar le va a
// fallar. Llamar después de requireAuth()/requireGerente(), no en su lugar.
function requireSucursalOperativa() {
  if (sesionVeTodo()) { location.href = '/'; return false; }
  return true;
}

// true solo para las sesiones que ven el negocio completo: las de una sucursal
// sin tienda asignada (Only Enterprises). El resto está restringida a su propia
// sucursal, así que no tiene caso ofrecerle filtrar por otras — es el mismo
// criterio que sucursal_restriccion() en main.py, que es quien manda.
function sesionVeTodo() {
  const s = getSesion();
  return !!s && !(s.tienda && s.tienda.length);
}

// ─── Logo según la tienda activa de la sesión ───────────────────────────────
// Cada submarca tiene su logo. Si la sesión no tiene una tienda única activa
// (sin restricción, ej. Only Enterprises, o una sucursal con varias tiendas
// como Imprenta), se usa el logo genérico de Only Enterprises.
const LOGOS_TIENDA = {
  'Only Reef': '/static/logo-only-reef.png',
  'Only Garden': '/static/logo-only-garden.png',
  'Only Pets': '/static/logo-only-pets.png',
  'Only Reptile': '/static/logo-only-reptile.png',
  'El Zar del LED': '/static/logo-zar-del-led.png',
};
// Logos de la(s) tienda(s) que recibe: varios cuando la sucursal tiene más de
// una activa (ej. Imprenta = Only Reef + Only Garden), y el genérico de Only
// Enterprises si no hay ninguna conocida.
function logosActivos(tiendas) {
  const conocidas = (tiendas || []).filter(t => LOGOS_TIENDA[t]);
  return conocidas.length ? conocidas.map(t => LOGOS_TIENDA[t]) : ['/static/logo.png'];
}

// Pinta uno o más logos dentro de un contenedor. El genérico de Only
// Enterprises se marca con logo-generico (se invierte en modo oscuro, ver
// modern.css); los de tienda son a color y no se invierten. Con más de un
// logo activo (Imprenta), se reduce un poco el tamaño para que quepan.
function renderLogos(contenedorId, tiendas, altoBase) {
  const cont = document.getElementById(contenedorId);
  if (!cont) return;
  const logos = logosActivos(tiendas);
  const alto = logos.length > 1 ? Math.round(altoBase * 0.72) : altoBase;
  cont.innerHTML = logos.map(src => {
    const generico = src === '/static/logo.png';
    return `<img class="brand-logo${generico ? ' logo-generico' : ''}" src="${src}" alt="Only Enterprises" style="height:${alto}px;width:auto;margin:0">`;
  }).join('');
}

// Devuelve {w, h} de una imagen (dataURL o URL). Los logos de tienda son
// verticales (icono + texto), a diferencia del logo ancho de Only
// Enterprises, así que el PDF debe calcular el ancho según la proporción
// real en vez de usar una caja fija, o se ve estirado.
function medirImagen(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => resolve({ w: 1, h: 1 });
    img.src = src;
  });
}

// ─── Diseño de la app por tienda ─────────────────────────────────────────────
// Retiñe el acento principal que ya usan casi todas las pantallas (--blue /
// --blue-bg: botones, selección, foco, insignias) al color de cada tienda, y
// agrega de fondo, muy tenue, las formas reales del ícono del logo como marca
// de agua — no un color inventado, la forma del logo. Mismos tonos (t1/t2)
// que el fondo animado del login, para que se sienta la misma identidad.
// Se activa solo con sesión.tienda === [una sola tienda]; con varias (ej.
// Imprenta) o ninguna (Only Enterprises) no cambia nada.
const TEMA_APP_TIENDA = {
  'Only Reef': {
    icono: '/static/logo-only-reef-icono.png',
    t1: '#0d3d66', t2: '#4fc3d9',
    claro: { acento: '#186a94', acentoBg: '#e6f1fb' },
    oscuro: { acento: '#5cc6dd', acentoBg: '#042c53' },
  },
  'Only Garden': {
    icono: '/static/logo-only-garden-icono.png',
    t1: '#0d3d17', t2: '#4caf50',
    claro: { acento: '#388e3c', acentoBg: '#eaf3de' },
    oscuro: { acento: '#8fd06a', acentoBg: '#173404' },
  },
  'Only Pets': {
    icono: '/static/logo-only-pets-icono.png',
    t1: '#122a52', t2: '#29b6d8',
    claro: { acento: '#0f7a94', acentoBg: '#e6f1fb' },
    oscuro: { acento: '#4fc3e0', acentoBg: '#042c53' },
  },
  'Only Reptile': {
    icono: '/static/logo-only-reptile-icono.png',
    t1: '#0f3d16', t2: '#7bc47f',
    claro: { acento: '#2e7d32', acentoBg: '#eaf3de' },
    oscuro: { acento: '#97c459', acentoBg: '#173404' },
  },
  'El Zar del LED': {
    // El texto va tejido en el propio escudo (no hay wordmark aparte que
    // recortar), así que la marca de agua usa el logo completo.
    icono: '/static/logo-zar-del-led.png',
    t1: '#3a0d0d', t2: '#c9a227',
    // Dorado en vez de rojo para el acento: el rojo ya significa "eliminar/
    // error" en el resto de la app (--red), usarlo de acento confundiría.
    claro: { acento: '#a5820f', acentoBg: '#faf3d9' },
    oscuro: { acento: '#e0b636', acentoBg: '#3a2e05' },
  },
};
// Only Enterprises (o cualquier sucursal sin tienda asignada): mismo fondo y
// vidrio que las demás, pero solo con la "O" del logo genérico, sin
// recolorear acentos (botones se quedan con el azul de siempre — "obscuro
// que ya tiene").
const TEMA_GENERICO = { icono: '/static/logo-o.png', t1: '#1a1a18', t2: '#3a3a36' };

function aplicarTemaTienda() {
  const s = getSesion();
  const tiendas = (s && s.tienda) || [];
  const oscuro = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (tiendas.length === 0) {
    _inyectarMarcaDeAguaTienda(TEMA_GENERICO.icono);
    _inyectarFondoTienda(TEMA_GENERICO.t1, TEMA_GENERICO.t2);
    _inyectarIconosTienda(); // sin color de fondo, borde neutro
    return;
  }

  if (tiendas.length === 1 && TEMA_APP_TIENDA[tiendas[0]]) {
    const tema = TEMA_APP_TIENDA[tiendas[0]];
    const paleta = oscuro ? tema.oscuro : tema.claro;
    document.documentElement.style.setProperty('--blue', paleta.acento);
    document.documentElement.style.setProperty('--blue-bg', paleta.acentoBg);
    _inyectarMarcaDeAguaTienda(tema.icono);
    _inyectarFondoTienda(tema.t1, tema.t2);
    _inyectarBotonesTienda();
    return;
  }

  // Sucursales con más de una tienda a la vez (ej. Imprenta = Only Reef +
  // Only Garden): se mezclan los dos acentos, y cada tienda pone su logo en
  // una esquina distinta en vez de competir por la misma.
  const temas = tiendas.map(t => TEMA_APP_TIENDA[t]).filter(Boolean);
  if (temas.length < 2) return;
  const [a, b] = temas;
  const pa = oscuro ? a.oscuro : a.claro;
  const pb = oscuro ? b.oscuro : b.claro;
  document.documentElement.style.setProperty('--blue', `color-mix(in srgb, ${pa.acento} 50%, ${pb.acento} 50%)`);
  document.documentElement.style.setProperty('--blue-bg', `color-mix(in srgb, ${pa.acentoBg} 50%, ${pb.acentoBg} 50%)`);
  _inyectarMarcaDeAguaTienda(a.icono, 'right:-30px;bottom:-20px;width:340px;transform:rotate(-6deg)', 'marca-agua-tienda');
  _inyectarMarcaDeAguaTienda(b.icono, 'left:-30px;top:64px;width:260px;transform:rotate(8deg)', 'marca-agua-tienda-2');
  _inyectarFondoTienda(a.t1, b.t1);
  _inyectarBotonesTienda();
}

function _inyectarMarcaDeAguaTienda(src, posicion, id) {
  id = id || 'marca-agua-tienda';
  if (document.getElementById(id) || !document.body) return;
  const img = document.createElement('img');
  img.id = id;
  img.src = src;
  img.alt = '';
  img.style.cssText = 'position:fixed;' + (posicion || 'right:-30px;bottom:-20px;width:420px;transform:rotate(-6deg)')
    + ';max-width:65vw;height:auto;opacity:.16;pointer-events:none;z-index:0;filter:saturate(1.3)';
  document.body.prepend(img);
}

// Fondo con el mismo tono y movimiento que el del login (degradado que se
// desplaza despacio), pero diluido para no competir con tablas/tarjetas.
function _inyectarFondoTienda(t1, t2) {
  if (document.getElementById('fondo-tienda') || !document.body) return;
  const style = document.createElement('style');
  style.textContent = `
    #fondo-tienda{position:fixed;inset:0;z-index:0;pointer-events:none;
      background:
        radial-gradient(circle at 12% 8%, color-mix(in srgb, ${t1} 28%, transparent), transparent 52%),
        radial-gradient(circle at 88% 92%, color-mix(in srgb, ${t2} 24%, transparent), transparent 55%);
      background-size:160% 160%;
      animation:fondo-tienda-mover 42s ease-in-out infinite}
    @keyframes fondo-tienda-mover{0%,100%{background-position:0% 0%}50%{background-position:100% 100%}}
    @media(prefers-reduced-motion:reduce){#fondo-tienda{animation:none}}
  `;
  document.head.appendChild(style);
  const div = document.createElement('div');
  div.id = 'fondo-tienda';
  document.body.prepend(div);
}

// Botones principales e íconos del menú con el acento de la tienda en vez
// del negro/blanco/ámbar genérico. La mayoría de las pantallas (precios,
// POS, etc.) ya usan var(--blue)/var(--green) en su botón principal, así que
// heredan el cambio solos; aquí solo se cubren los que usan un color fijo.
function _inyectarBotonesTienda() {
  if (document.getElementById('botones-tienda')) return;
  const style = document.createElement('style');
  style.id = 'botones-tienda';
  style.textContent = `.btn, button.primary, .btn-primary, .btn-agregar{
    background:var(--blue) !important;color:#fff !important;border-color:var(--blue) !important}`;
  document.head.appendChild(style);
  _inyectarIconosTienda('var(--blue)');
}

// Empareja los íconos del menú principal (precios/pagos/clientes/gastos/
// inventario, hoy en 3 colores distintos) a un solo tono: sin relleno, solo
// un borde — de la tienda si la hay, o neutro para Only Enterprises.
function _inyectarIconosTienda(colorBorde) {
  if (document.getElementById('iconos-tienda')) return;
  const style = document.createElement('style');
  style.id = 'iconos-tienda';
  style.textContent = `.icon-precios, .icon-pagos, .icon-inv{
    background:transparent !important;border:1px solid ${colorBorde || 'var(--border)'}}`;
  document.head.appendChild(style);
}

// ─── Caché de logos en base64 (compartida por tickets/recibos/cotizaciones) ─
// Antes cada pantalla duplicaba esto con una sola casilla de caché (_logoCacheDataUrl),
// lo que pisaba el logo cacheado si una misma página usaba más de uno (ej.
// historial.html: el logo de la tienda en el ticket Y el genérico en el
// reporte consolidado). Aquí el caché es por URL (+ resolución, ej. las
// cotizaciones en PDF carta usan más resolución que un ticket de 58mm).
const _logoCache = {};
function cargarImagenBase64(url, anchoDestino = 240) {
  const clave = url + '@' + anchoDestino;
  if (_logoCache[clave]) return Promise.resolve(_logoCache[clave]);
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const alto = Math.round(img.height * (anchoDestino / img.width));
      const canvas = document.createElement('canvas');
      canvas.width = anchoDestino;
      canvas.height = alto;
      canvas.getContext('2d').drawImage(img, 0, 0, anchoDestino, alto);
      const dataUrl = canvas.toDataURL('image/png');
      _logoCache[clave] = dataUrl;
      resolve(dataUrl);
    };
    img.onerror = reject;
    img.src = url;
  });
}

// Precarga (sin bloquear) el o los logos de la tienda activa de la sesión.
function precargarLogosActivos() {
  const s = getSesion();
  logosActivos(s && s.tienda).forEach(src => cargarImagenBase64(src).catch(() => {}));
}

// HTML de <img> para insertar en un ticket/recibo/cotización: uno o varios
// logos según cuántas tiendas tenga activa la sesión (Imprenta = 2). Usa el
// data-URL cacheado si ya está listo (necesario para que html2canvas/jsPDF
// lo capturen sin depender de una carga de red durante la captura); si no,
// cae al archivo directo (el navegador lo resuelve igual en pantalla).
function logosTicketHTML(alturaPx) {
  const s = getSesion();
  const logos = logosActivos(s && s.tienda);
  const alto = logos.length > 1 ? Math.round(alturaPx * 0.72) : alturaPx;
  return logos.map(src => {
    const cached = _logoCache[src + '@240'];
    return `<img class="tk-logo" src="${cached || src}" alt="Only Enterprises" style="height:${alto}px;width:auto;margin:0 4px 6px">`;
  }).join('');
}

// Versión "silueta" de cada logo (negro sólido donde hay forma, sin
// degradado) para impresoras térmicas: son de 1 bit, así que cualquier gris
// intermedio lo resuelven a puntos (dithering) y las partes más delgadas del
// logo (ej. la punta de la luna) se pierden. Con negro sólido no hay nada
// que difuminar.
const LOGOS_SILUETA = {
  '/static/logo.png': '/static/logo-silueta.png',
  '/static/logo-only-reef.png': '/static/logo-only-reef-silueta.png',
  '/static/logo-only-garden.png': '/static/logo-only-garden-silueta.png',
  '/static/logo-only-pets.png': '/static/logo-only-pets-silueta.png',
  '/static/logo-only-reptile.png': '/static/logo-only-reptile-silueta.png',
  '/static/logo-zar-del-led.png': '/static/logo-zar-del-led-silueta.png',
};

// Para la ventana de impresión: reemplaza cualquier data-URL cacheado que
// haya quedado embebido en el HTML de vuelta por la versión silueta (no la
// de color original — evita además mandar un document.write() con base64
// gigante a la ventana nueva).
function reemplazarLogosPorURL(html) {
  let out = html;
  Object.keys(_logoCache).forEach(clave => {
    const url = clave.slice(0, clave.lastIndexOf('@'));
    out = out.split(_logoCache[clave]).join(LOGOS_SILUETA[url] || url);
  });
  return out;
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

// ─── Asistente flotante ────────────────────────────────────────────────────
// El robot de la esquina vive en su propio archivo y se carga desde aquí,
// que es lo único que incluyen todas las pantallas. Se monta solo si hay
// sesión, así que en /login no aparece.
(function(){
  if (!getSesion()) return;
  const s = document.createElement('script');
  s.src = '/static/chat-widget.js?v=1787605997';
  s.defer = true;
  document.head.appendChild(s);
})();
