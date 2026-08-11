#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Agrega confirmarPersonalizado() y promptPersonalizado() a auth.js,
compartido por TODAS las paginas (se inyectan solos, con estilos inline
para no depender del CSS de cada pagina).
Uso: cd ~/inventario-qa/static && python3 qa_modales_centralizados.py
"""
import os

AUTH = os.path.expanduser('~/inventario-qa/static/auth.js')
src = open(AUTH, encoding='utf-8').read()

if 'function confirmarPersonalizado' in src:
    print("* Ya existia, se omite")
else:
    bloque = '''

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
'''
    src = src.rstrip('\n') + bloque
    open(AUTH, 'w', encoding='utf-8').write(src)
    print("OK: confirmarPersonalizado() y promptPersonalizado() agregadas a auth.js")

print()
print("=" * 55)
print("Reiniciando inventario-qa (NO produccion)...")
os.system("sudo systemctl restart inventario-qa")
print("Listo. Estas funciones ya estan disponibles en TODAS las paginas")
print("que cargan auth.js (que son todas). El siguiente paso es reemplazar")
print("los confirm()/prompt() de cada pagina para que las usen.")
