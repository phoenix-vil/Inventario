// ─── Asistente flotante ─────────────────────────────────────────────────────
// Un robot en la esquina que abre el chat sin salir de la pantalla en la que
// estás. Lo carga auth.js, así que vive en todas las páginas con sesión.
//
// El panel lleva las clases `overlay open` mientras está abierto: así auth.js
// no recarga la página a media conversación (ver el chequeo periódico ahí).
(function () {
  if (window.__chatWidget) return;          // que no se monte dos veces
  window.__chatWidget = true;

  const CSS = `
.robot-fab{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom));z-index:60;
  width:54px;height:54px;border-radius:50%;border:none;cursor:pointer;
  background:var(--text,#1a1a18);color:var(--bg2,#fff);
  box-shadow:0 4px 16px rgba(0,0,0,.22);display:flex;align-items:center;justify-content:center;
  transition:transform .18s cubic-bezier(.3,1.4,.5,1),opacity .18s;-webkit-tap-highlight-color:transparent}
.robot-fab:active{transform:scale(.92)}
.robot-fab.oculto{transform:scale(.4);opacity:0;pointer-events:none}
.robot-fab svg{width:30px;height:30px}
.robot-ojo{transform-origin:center;animation:robot-parpadeo 5.5s infinite}
@keyframes robot-parpadeo{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.15)}}
.robot-antena{transform-origin:16px 8px;animation:robot-antena 4s ease-in-out infinite}
@keyframes robot-antena{0%,100%{transform:rotate(-7deg)}50%{transform:rotate(7deg)}}
@media(prefers-reduced-motion:reduce){.robot-ojo,.robot-antena{animation:none}}

.robot-panel{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom));z-index:61;
  width:min(380px,calc(100vw - 32px));height:min(560px,70vh);
  background:var(--bg2,#fff);border:0.5px solid var(--border,#e2e0d8);border-radius:18px;
  box-shadow:0 12px 40px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;
  transform-origin:bottom right}
.robot-panel.abierto{display:flex;animation:robot-entra .2s cubic-bezier(.3,1.2,.5,1)}
@keyframes robot-entra{from{opacity:0;transform:scale(.9) translateY(12px)}to{opacity:1;transform:none}}
@media(max-width:520px){.robot-panel{right:8px;left:8px;width:auto;height:min(78vh,620px)}}

.robot-cab{display:flex;align-items:center;gap:9px;padding:.7rem .8rem;
  border-bottom:0.5px solid var(--border,#e2e0d8);flex-shrink:0}
.robot-cab-t{font-size:14px;font-weight:700;flex:1;color:var(--text,#1a1a18)}
.robot-cab-s{font-size:11px;color:var(--text2,#6b6b66);font-weight:400}
.robot-cab button{width:30px;height:30px;border:none;background:transparent;cursor:pointer;
  color:var(--text2,#6b6b66);font-size:15px;border-radius:8px;flex-shrink:0}
.robot-cab button:hover{background:var(--bg,#f5f4f0)}

.robot-hilo{flex:1;overflow-y:auto;padding:.9rem;display:flex;flex-direction:column;gap:9px;
  -webkit-overflow-scrolling:touch}
.robot-msg{max-width:90%;padding:.55rem .75rem;border-radius:14px;font-size:14px;line-height:1.42;
  white-space:pre-wrap;word-wrap:break-word}
.robot-msg.yo{align-self:flex-end;background:var(--text,#1a1a18);color:var(--bg2,#fff);border-bottom-right-radius:4px}
.robot-msg.bot{align-self:flex-start;background:var(--bg,#f5f4f0);color:var(--text,#1a1a18);
  border:0.5px solid var(--border,#e2e0d8);border-bottom-left-radius:4px}
.robot-msg.err{background:var(--red-bg,#fcebeb);color:var(--red,#a32d2d);border-color:transparent}

.robot-pie{align-self:flex-start;font-size:10px;color:var(--text2,#6b6b66);margin-top:-5px;
  display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding-left:3px}
.robot-tool{font-weight:700;padding:1px 7px;border-radius:20px;
  background:var(--blue-bg,#e6f1fb);color:var(--blue,#185fa5)}
.robot-ver{background:none;border:none;color:var(--text2,#6b6b66);font-size:10px;cursor:pointer;
  text-decoration:underline;padding:0;font-family:inherit}
.robot-datos{align-self:flex-start;max-width:90%;background:var(--bg,#f5f4f0);
  border:0.5px solid var(--border,#e2e0d8);border-radius:10px;padding:.5rem .6rem;font-size:10px;
  font-family:ui-monospace,Menlo,monospace;color:var(--text2,#6b6b66);white-space:pre-wrap;
  overflow-x:auto;display:none}
.robot-datos.abierto{display:block}

.robot-sug{display:flex;gap:6px;flex-wrap:wrap;padding:0 .9rem .5rem;flex-shrink:0}
.robot-sug button{height:30px;padding:0 10px;border:0.5px solid var(--border,#e2e0d8);border-radius:16px;
  background:var(--bg2,#fff);color:var(--text,#1a1a18);font-size:12px;cursor:pointer;
  font-family:inherit;white-space:nowrap}
.robot-sug button:active{background:var(--bg,#f5f4f0)}

.robot-barra{display:flex;gap:7px;padding:.6rem .8rem calc(.6rem + env(safe-area-inset-bottom));
  border-top:0.5px solid var(--border,#e2e0d8);flex-shrink:0}
.robot-barra input{flex:1;height:40px;padding:0 12px;border:0.5px solid var(--border,#e2e0d8);
  border-radius:20px;background:var(--bg,#f5f4f0);color:var(--text,#1a1a18);font-size:16px;
  font-family:inherit}
.robot-barra input:focus{outline:none;border-color:var(--blue,#185fa5)}
.robot-barra button{width:40px;height:40px;border:none;border-radius:20px;
  background:var(--text,#1a1a18);color:var(--bg2,#fff);font-size:17px;cursor:pointer;flex-shrink:0}
.robot-barra button:disabled{opacity:.4}

.robot-pensando{align-self:flex-start;display:flex;gap:4px;padding:.6rem .75rem;
  background:var(--bg,#f5f4f0);border:0.5px solid var(--border,#e2e0d8);border-radius:14px}
.robot-pensando i{width:6px;height:6px;border-radius:50%;background:var(--text2,#6b6b66);
  animation:robot-latir 1.2s infinite}
.robot-pensando i:nth-child(2){animation-delay:.2s}
.robot-pensando i:nth-child(3){animation-delay:.4s}
@keyframes robot-latir{0%,60%,100%{opacity:.25}30%{opacity:1}}
`;

  // Robot de trazo: hereda el color del botón, así queda bien en claro y oscuro.
  const ROBOT = `
<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.9"
     stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <g class="robot-antena">
    <path d="M16 8V4.5"/>
    <circle cx="16" cy="3" r="1.5" fill="currentColor" stroke="none"/>
  </g>
  <rect x="4.5" y="8" width="23" height="17" rx="5.5"/>
  <ellipse class="robot-ojo" cx="11.5" cy="15.5" rx="1.9" ry="2.2" fill="currentColor" stroke="none"/>
  <ellipse class="robot-ojo" cx="20.5" cy="15.5" rx="1.9" ry="2.2" fill="currentColor" stroke="none"/>
  <path d="M12.5 20.2h7"/>
  <path d="M1.8 14v4M30.2 14v4"/>
</svg>`;

  const SUG_BASE = ['¿A cuánto vendo…?', '¿Qué se está acabando?', '¿Dónde hay…?'];
  const SUG_GERENTE = ['¿Ventas de hoy?', '¿Quién me debe?', '¿Gastos del mes?'];

  let hilo, entrada, enviarBtn, panel, fab, ocupado = false, saludado = false;

  function montar() {
    const estilo = document.createElement('style');
    estilo.textContent = CSS;
    document.head.appendChild(estilo);

    fab = document.createElement('button');
    fab.className = 'robot-fab';
    fab.setAttribute('aria-label', 'Abrir el asistente');
    fab.innerHTML = ROBOT;
    fab.onclick = abrir;

    panel = document.createElement('div');
    // `overlay` + `open` (al abrirse) frenan la recarga automática de auth.js
    panel.className = 'robot-panel overlay';
    panel.innerHTML = `
      <div class="robot-cab">
        <span style="width:26px;height:26px;display:flex;color:var(--text)">${ROBOT}</span>
        <div class="robot-cab-t">Asistente<div class="robot-cab-s">solo consulta</div></div>
        <button title="Limpiar" data-accion="limpiar">🗑</button>
        <button title="Cerrar" data-accion="cerrar">✕</button>
      </div>
      <div class="robot-hilo"></div>
      <div class="robot-sug"></div>
      <div class="robot-barra">
        <input placeholder="Pregunta algo…" autocomplete="off" enterkeyhint="send">
        <button title="Enviar">↑</button>
      </div>`;

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    hilo = panel.querySelector('.robot-hilo');
    entrada = panel.querySelector('.robot-barra input');
    enviarBtn = panel.querySelector('.robot-barra button');

    enviarBtn.onclick = enviar;
    entrada.onkeydown = (e) => { if (e.key === 'Enter') enviar(); };
    panel.querySelector('[data-accion="cerrar"]').onclick = cerrar;
    panel.querySelector('[data-accion="limpiar"]').onclick = () => {
      hilo.innerHTML = '';
      saludado = false;
      saludar();
    };
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && panel.classList.contains('abierto')) cerrar();
    });

    pintarSugerencias();
    acomodar();
    let temporizador;
    window.addEventListener('resize', () => {
      clearTimeout(temporizador);
      temporizador = setTimeout(acomodar, 150);
    });
  }

  function pintarSugerencias() {
    const gerente = (typeof esGerente === 'function') && esGerente();
    const lista = gerente ? SUG_BASE.concat(SUG_GERENTE) : SUG_BASE;
    const cont = panel.querySelector('.robot-sug');
    cont.innerHTML = lista.map((s) => `<button>${s}</button>`).join('');
    cont.querySelectorAll('button').forEach((b) => {
      b.onclick = () => {
        // Las sugerencias con "…" son plantillas: se dejan escritas para completar
        if (b.textContent.includes('…')) {
          entrada.value = b.textContent.replace('…', '');
          entrada.focus();
        } else {
          entrada.value = b.textContent;
          enviar();
        }
      };
    });
  }

  function saludar() {
    if (saludado) return;
    saludado = true;
    burbuja('Pregúntame por precios, existencias o cómo van las ventas.', 'bot');
  }

  function abrir() {
    acomodar();
    panel.classList.add('abierto', 'open');
    fab.classList.add('oculto');
    saludar();
    // En el teléfono, enfocar de inmediato levanta el teclado y tapa el panel
    if (window.innerWidth > 520) entrada.focus();
  }

  function cerrar() {
    panel.classList.remove('abierto', 'open');
    fab.classList.remove('oculto');
  }

  // El punto de venta tiene la barra del total fija abajo (.totales), y otras
  // pantallas pueden tener lo suyo. En vez de esconder el robot ahí —que es
  // justo donde te preguntas un precio— se busca qué hay debajo y se sube por
  // encima. Se recalcula al abrir y al cambiar el tamaño de la ventana.
  function acomodar() {
    fab.style.bottom = '';
    panel.style.bottom = '';
    const zona = fab.getBoundingClientRect();
    const alto = window.innerHeight;
    let tope = alto;

    document.querySelectorAll('body *').forEach((el) => {
      if (el === fab || el === panel || panel.contains(el) || fab.contains(el)) return;
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'sticky') return;
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.1) return;
      const b = el.getBoundingClientRect();
      if (b.height === 0 || b.height > alto * 0.4) return;   // eso no es una barra
      if (b.bottom < alto * 0.5) return;                     // no está abajo
      const cruza = b.right > zona.left && b.left < zona.right
                 && b.top < zona.bottom && b.bottom > zona.top;
      if (cruza) tope = Math.min(tope, b.top);
    });

    if (tope < alto) {
      const sube = `calc(${Math.round(alto - tope + 12)}px + env(safe-area-inset-bottom))`;
      fab.style.bottom = sube;
      panel.style.bottom = sube;
    }
  }

  function alFinal() { hilo.scrollTop = hilo.scrollHeight; }

  function burbuja(texto, clase) {
    const d = document.createElement('div');
    d.className = 'robot-msg ' + clase;
    d.textContent = texto;
    hilo.appendChild(d);
    alFinal();
    return d;
  }

  function pie(r) {
    if (!r.herramienta) return;
    const p = document.createElement('div');
    p.className = 'robot-pie';
    const args = r.argumentos && Object.keys(r.argumentos).length
      ? Object.entries(r.argumentos).map(([k, v]) => `${k}: ${v}`).join(', ') : '';
    p.innerHTML = `<span class="robot-tool">${r.herramienta}</span><span>${args}</span>`;

    const caja = document.createElement('div');
    caja.className = 'robot-datos';
    caja.textContent = 'Dato verificado: ' + (r.resumen_verificado || '—')
      + '\n\n' + JSON.stringify(r.datos, null, 1);

    const ver = document.createElement('button');
    ver.className = 'robot-ver';
    ver.textContent = 'ver datos';
    ver.onclick = () => {
      caja.classList.toggle('abierto');
      ver.textContent = caja.classList.contains('abierto') ? 'ocultar' : 'ver datos';
      alFinal();
    };
    p.appendChild(ver);
    hilo.appendChild(p);
    hilo.appendChild(caja);
    alFinal();
  }

  async function enviar() {
    const mensaje = entrada.value.trim();
    if (!mensaje || ocupado) return;

    burbuja(mensaje, 'yo');
    entrada.value = '';
    ocupado = true;
    enviarBtn.disabled = true;

    const puntos = document.createElement('div');
    puntos.className = 'robot-pensando';
    puntos.innerHTML = '<i></i><i></i><i></i>';
    hilo.appendChild(puntos);
    alFinal();

    try {
      const r = await authFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje, tz_offset_min: new Date().getTimezoneOffset() })
      });
      puntos.remove();
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        burbuja(e.detail || 'No pude responder. Intenta de nuevo.', 'bot err');
      } else {
        const data = await r.json();
        burbuja(data.respuesta, 'bot');
        pie(data);
      }
    } catch (e) {
      puntos.remove();
      burbuja('Se perdió la conexión con el servidor.', 'bot err');
    } finally {
      ocupado = false;
      enviarBtn.disabled = false;
      alFinal();
    }
  }

  function iniciar() {
    // Sin sesión no hay asistente (login, por ejemplo)
    if (typeof getSesion !== 'function' || !getSesion()) return;
    montar();
    if (window.CHAT_ABRIR_AL_CARGAR) abrir();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }

  window.abrirChat = () => (panel ? abrir() : null);
})();
