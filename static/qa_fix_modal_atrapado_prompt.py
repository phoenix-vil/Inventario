#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Saca el modal de prompt generico de donde quedo atrapado (dentro
del string de imprimirTicket()) y lo reinserta correctamente al final
real del archivo.
Uso: cd ~/inventario-qa/static && python3 qa_fix_modal_atrapado_prompt.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# ================================================================
# 1. Quitar el modal atrapado dentro del string de imprimirTicket()
# ================================================================
patron = re.compile(
    re.escape('${generarTicketHTML(ticketActual)}') + r'.*?' + re.escape('</body></html>`);'),
    re.DOTALL
)
m = patron.search(src)
if m:
    src = patron.sub('${generarTicketHTML(ticketActual)}</body></html>`);', src, count=1)
    print("1. imprimirTicket() restaurado (modal atrapado removido)")
else:
    print("1. * No se encontro contenido atrapado, revisar manualmente")

# ================================================================
# 2. Insertar el modal correctamente al final real del archivo
# ================================================================
if 'id="prompt-generico-modal"' not in src:
    modal_html = '''
<!-- Modal de prompt generico (reemplaza prompt() nativo) -->
<div class="overlay" id="prompt-generico-modal">
  <div class="modal">
    <h2 id="prompt-generico-titulo">Escribe un valor</h2>
    <p id="prompt-generico-mensaje" style="font-size:13px;color:var(--text2);margin-bottom:12px"></p>
    <div class="field"><input type="text" id="prompt-generico-input" autocomplete="off"></div>
    <div class="modal-footer">
      <button onclick="_cancelarPromptGenerico()">Cancelar</button>
      <button class="primary" onclick="_aceptarPromptGenerico()">Aceptar</button>
    </div>
  </div>
</div>
'''
    patron_final = re.compile(r'</script>\s*</body>\s*</html>\s*$')
    nueva_src, n = patron_final.subn('</script>' + modal_html + '\n</body>\n</html>\n', src, count=1)
    if n == 1:
        src = nueva_src
        print("2. Modal insertado correctamente al final real del archivo")
    else:
        print("2. ERROR: no se encontro el patron final del archivo")
else:
    print("2. * El modal ya existe en algun lado, revisar si quedo bien puesto")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Prueba de nuevo: Dejar en espera Y tambien Imprimir un ticket")
    print("(ambos usaban la misma zona que se rompio).")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
