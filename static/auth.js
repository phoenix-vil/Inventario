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
