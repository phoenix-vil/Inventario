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
/* Sin círculo de fondo: el robot flota libre sobre la página. La silueta ya
   lleva contorno oscuro en cada pieza (ver robotSVG) precisamente para
   leerse bien encima de cualquier fondo, claro u oscuro, así que no hace
   falta la placa detrás. El botón sigue midiendo 68x68 para el área de
   toque, solo que ahora es invisible. */
.robot-fab{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom));z-index:60;
  width:68px;height:68px;border-radius:50%;border:none;cursor:pointer;
  background:transparent;display:flex;align-items:center;justify-content:center;
  transition:transform .18s cubic-bezier(.3,1.4,.5,1),opacity .18s;-webkit-tap-highlight-color:transparent}
.robot-fab:active{transform:scale(.92)}
.robot-fab.oculto{transform:scale(.4);opacity:0;pointer-events:none}
.robot-fab svg{width:43px;height:56px;overflow:visible;
  filter:drop-shadow(0 3px 5px rgba(0,0,0,.35))}
/* "Vuelo": más recorrido vertical que un simple flote, más el balanceo
   (rotate) de lado a lado -- da la sensación de estar planeando, no solo
   subiendo y bajando en el mismo sitio. */
.robot-cuerpo{transform-box:fill-box;transform-origin:50% 50%;animation:robot-volar 3s ease-in-out infinite}
@keyframes robot-volar{
  0%,100%{transform:translate(0,0) rotate(-3deg)}
  50%{transform:translate(1.5px,-7px) rotate(3deg)}
}
.robot-ojo{transform-box:fill-box;transform-origin:center;animation:robot-parpadeo 5.5s infinite}
@keyframes robot-parpadeo{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.15)}}
.robot-brillo{transform-box:fill-box;transform-origin:center;animation:robot-brillo-pulso 2.4s ease-in-out infinite}
@keyframes robot-brillo-pulso{0%,100%{opacity:.65;transform:scale(.9)}50%{opacity:1;transform:scale(1.1)}}
/* Propulsores: laten al revés que el cuerpo (más brillantes cuando el
   cuerpo sube), para que se lea como el empuje que lo hace volar. */
.robot-propulsor{transform-box:fill-box;transform-origin:50% 0%;animation:robot-propulsor-pulso 3s ease-in-out infinite}
@keyframes robot-propulsor-pulso{
  0%,100%{opacity:.55;transform:scaleY(.8)}
  50%{opacity:1;transform:scaleY(1.25)}
}
.robot-brazo{transform-box:fill-box;transform-origin:50% 0%;animation:robot-brazo-mece 3.6s ease-in-out infinite}
@keyframes robot-brazo-mece{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}
@media(prefers-reduced-motion:reduce){.robot-cuerpo,.robot-ojo,.robot-brillo,.robot-brazo,.robot-propulsor{animation:none}}

/* Globo de invitación: aparece solo, una vez por sesión (ver mostrarGlobo),
   señalando al robot. El bottom se calcula junto con el del botón en
   acomodar(), para que también se suba si hay una barra fija abajo.
   Entra y sale con @keyframes (no con transition): con solo transition, al
   pasar de "display:none" a mostrado, la primera pintura no siempre alcanza
   a interpolar -- con una animación de un solo tramo (forwards) siempre
   arranca del fotograma inicial que se le pide, sin depender de ese primer
   pintado. */
.robot-globo{position:fixed;right:16px;z-index:59;max-width:180px;
  background:var(--bg2,#fff);color:var(--text,#1a1a18);
  border:0.5px solid var(--border,#e2e0d8);border-radius:14px 14px 3px 14px;
  padding:9px 13px;font-size:13px;line-height:1.35;font-weight:600;
  box-shadow:0 6px 18px rgba(0,0,0,.16);cursor:pointer;transform-origin:bottom right;
  opacity:0;pointer-events:none;display:none}
.robot-globo.visible{display:block;pointer-events:auto;
  animation:robot-globo-entra .32s cubic-bezier(.3,1.4,.5,1) forwards}
.robot-globo.saliendo{display:block;
  animation:robot-globo-sale .22s ease-in forwards}
@keyframes robot-globo-entra{
  from{opacity:0;transform:scale(.35) translateY(6px)}
  to{opacity:1;transform:scale(1) translateY(0)}
}
@keyframes robot-globo-sale{
  from{opacity:1;transform:scale(1) translateY(0)}
  to{opacity:0;transform:scale(.5) translateY(4px)}
}
@media(prefers-reduced-motion:reduce){
  .robot-globo.visible{animation:none;opacity:1;transform:none}
  .robot-globo.saliendo{animation:none;opacity:0}
}

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

  // Robot de cuerpo completo, con degradados para el efecto "de juguete 3D"
  // (en vez de un modelo 3D real vía WebGL: eso sería mucho para un ícono que
  // vive todo el tiempo en pantalla, sobre todo en el iPhone). El contorno
  // oscuro en cada pieza es lo que lo hace legible tanto sobre el botón claro
  // como el oscuro (el botón invierte con el tema — ver .robot-fab arriba).
  // Se llama con un sufijo distinto en cada aparición (botón y encabezado del
  // panel) para que los degradados <defs> no compartan id en el documento.
  function robotSVG(id) {
    return `
<svg viewBox="0 0 100 130" fill="none" aria-hidden="true">
  <defs>
    <linearGradient id="rgHead-${id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#eaf7ff"/><stop offset="1" stop-color="#5b9fdb"/>
    </linearGradient>
    <linearGradient id="rgTorso-${id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#c2d5e8"/>
    </linearGradient>
    <linearGradient id="rgVisor-${id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1c3a5e"/><stop offset="1" stop-color="#0a1520"/>
    </linearGradient>
    <linearGradient id="rgMetal-${id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f3f6f9"/><stop offset="1" stop-color="#aab9ca"/>
    </linearGradient>
    <radialGradient id="rgGlow-${id}" cx=".35" cy=".3" r=".75">
      <stop offset="0" stop-color="#fff3c4"/><stop offset=".55" stop-color="#ffce54"/><stop offset="1" stop-color="#f5a623"/>
    </radialGradient>
  </defs>
  <g class="robot-cuerpo" stroke="#16263b" stroke-width="2.2" stroke-linejoin="round">
    <line x1="50" y1="14" x2="50" y2="4" stroke="url(#rgMetal-${id})" stroke-width="4" stroke-linecap="round"/>
    <circle class="robot-brillo" cx="50" cy="4" r="5" fill="url(#rgGlow-${id})" stroke-width="1.4"/>
    <ellipse class="robot-propulsor" cx="35" cy="122" rx="4.2" ry="6" fill="url(#rgGlow-${id})" stroke="none"/>
    <ellipse class="robot-propulsor" cx="65" cy="122" rx="4.2" ry="6" fill="url(#rgGlow-${id})" stroke="none" style="animation-delay:-1.5s"/>
    <rect x="26" y="100" width="48" height="16" rx="8" fill="url(#rgMetal-${id})"/>
    <rect class="robot-brazo" x="6" y="66" width="15" height="32" rx="7.5" fill="url(#rgMetal-${id})"/>
    <rect class="robot-brazo" x="79" y="66" width="15" height="32" rx="7.5" fill="url(#rgMetal-${id})" style="animation-delay:-1.8s"/>
    <rect x="20" y="62" width="60" height="40" rx="20" fill="url(#rgTorso-${id})"/>
    <circle class="robot-brillo" cx="50" cy="82" r="6.5" fill="url(#rgGlow-${id})" stroke-width="1.4" style="animation-delay:-1.2s"/>
    <rect x="44" y="56" width="12" height="8" rx="3" fill="url(#rgMetal-${id})" stroke-width="1.8"/>
    <rect x="22" y="14" width="56" height="42" rx="18" fill="url(#rgHead-${id})"/>
    <rect x="30" y="28" width="40" height="18" rx="9" fill="url(#rgVisor-${id})" stroke="#0a1520" stroke-width="1.5"/>
    <circle class="robot-ojo" cx="42" cy="37" r="4.3" fill="#8fe9ff" stroke="none"/>
    <circle class="robot-ojo" cx="58" cy="37" r="4.3" fill="#8fe9ff" stroke="none"/>
    <circle cx="43.2" cy="35.5" r="1.1" fill="#fff" opacity=".85" stroke="none"/>
    <circle cx="59.2" cy="35.5" r="1.1" fill="#fff" opacity=".85" stroke="none"/>
  </g>
</svg>`;
  }

  const SUG_BASE = ['¿A cuánto vendo…?', '¿Qué se está acabando?', '¿Dónde hay…?'];
  const SUG_GERENTE = ['¿Ventas de hoy?', '¿Quién me debe?', '¿Gastos del mes?'];

  let hilo, entrada, enviarBtn, panel, fab, globo, ocupado = false, saludado = false;
  let temporizadorOcultarGlobo;

  function montar() {
    const estilo = document.createElement('style');
    estilo.textContent = CSS;
    document.head.appendChild(estilo);

    fab = document.createElement('button');
    fab.className = 'robot-fab';
    fab.setAttribute('aria-label', 'Abrir el asistente');
    fab.innerHTML = robotSVG('fab');
    fab.onclick = abrir;

    panel = document.createElement('div');
    // `overlay` + `open` (al abrirse) frenan la recarga automática de auth.js
    panel.className = 'robot-panel overlay';
    panel.innerHTML = `
      <div class="robot-cab">
        <span style="width:20px;height:26px;display:flex;flex-shrink:0">${robotSVG('cab')}</span>
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

    globo = document.createElement('div');
    globo.className = 'robot-globo';
    globo.textContent = 'Puedes preguntarme algo';
    globo.onclick = abrir;

    document.body.appendChild(fab);
    document.body.appendChild(panel);
    document.body.appendChild(globo);

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

    // Invitación a preguntar: una sola vez por sesión de navegador, no en
    // cada página que se visita -- si no, se vuelve molesta. sessionStorage
    // se borra al cerrar la pestaña/PWA, así que en la siguiente sesión de
    // trabajo se vuelve a mostrar una vez.
    try {
      if (!sessionStorage.getItem('robot_globo_visto')) {
        sessionStorage.setItem('robot_globo_visto', '1');
        setTimeout(mostrarGlobo, 3000);
      }
    } catch (e) { /* modo privado sin sessionStorage: sin invitación, no rompe nada */ }
  }

  function mostrarGlobo() {
    // Si ya se abrió el chat (o CHAT_ABRIR_AL_CARGAR lo abrió de una vez en
    // /chat) no tiene caso invitar a algo que ya está pasando.
    if (!globo || panel.classList.contains('abierto')) return;
    acomodar();
    globo.classList.remove('saliendo');
    globo.classList.add('visible');
    clearTimeout(temporizadorOcultarGlobo);
    temporizadorOcultarGlobo = setTimeout(ocultarGlobo, 5000);
  }

  function ocultarGlobo() {
    clearTimeout(temporizadorOcultarGlobo);
    if (!globo || !globo.classList.contains('visible')) return;
    globo.classList.remove('visible');
    globo.classList.add('saliendo');
    // Quitar "saliendo" al terminar su propia animación (220ms), para que
    // vuelva a display:none y no se quede estorbando al toque en el robot.
    setTimeout(() => globo.classList.remove('saliendo'), 260);
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
    ocultarGlobo();
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

    // El globo va siempre pegado justo encima del robot -- se mide la
    // posición final del botón (ya con el ajuste de arriba aplicado, si
    // hubo) en vez de recalcular aparte, para no repetir esa lógica.
    if (globo) {
      const r = fab.getBoundingClientRect();
      globo.style.bottom = `${Math.round(alto - r.top + 10)}px`;
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
