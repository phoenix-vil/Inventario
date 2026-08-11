#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Inserta el modal de prompt generico justo antes del </body> real,
usando el contenido exacto confirmado con cat -A.
Uso: cd ~/inventario-qa/static && python3 qa_insertar_modal_correcto.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario-qa/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()

if 'id="prompt-generico-modal"' in src:
    print("* El modal ya existe en el archivo, no se hace nada")
else:
    viejo_final = '''      <button class="primary" onclick="_resolverConfirmarGenerico(true)">Continuar</button>
    </div>
  </div>
</div>

</body>
</html>'''

    modal_html = '''<!-- Modal de prompt generico (reemplaza prompt() nativo) -->
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
</div>'''

    nuevo_final = '''      <button class="primary" onclick="_resolverConfirmarGenerico(true)">Continuar</button>
    </div>
  </div>
</div>

''' + modal_html + '''

</body>
</html>'''

    n = src.count(viejo_final)
    if n == 1:
        src = src.replace(viejo_final, nuevo_final, 1)
        open(PAGOS, 'w', encoding='utf-8').write(src)
        print("OK: modal insertado correctamente antes del </body> real")
    else:
        print("ERROR: no se encontro el patron exacto (coincidencias: " + str(n) + ")")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
ok = all(s.count('{') == s.count('}') for s in scripts)

print()
if ok:
    print("Balance de llaves OK. Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. Prueba de nuevo: Dejar en espera Y tambien Imprimir un ticket.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
