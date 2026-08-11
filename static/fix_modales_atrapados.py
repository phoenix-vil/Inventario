#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRIGE BUG CRITICO: los modales "pendientes-modal" y "modal-confirmar-generico"
quedaron atrapados dentro del string de JavaScript de imprimirTicket()
(porque scripts anteriores buscaron '</body>' y encontraron por error el
que aparece DENTRO de ese string, no el cierre real de la pagina).

Este script:
1. Restaura imprimirTicket() a su forma correcta (sin los modales adentro)
2. Inserta ambos modales como HTML real, en el lugar correcto: despues
   de que cierra el <script> pero antes del </body> verdadero.

Uso: cd ~/inventario/static && python3 fix_modales_atrapados.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# ================================================================
# 1. Restaurar imprimirTicket(): quitar los modales atrapados en el string
# ================================================================
viejo_roto = '''    </style></head><body>${generarTicketHTML(ticketActual)}
<!-- Modal ventas en espera -->
<div class="overlay" id="pendientes-modal">
  <div class="modal">
    <h2>⏸ Ventas en espera</h2>
    <div id="pendientes-lista" style="max-height:340px;overflow-y:auto"></div>
    <div class="modal-footer">
      <button onclick="cerrarPendientes()">Cerrar</button>
    </div>
  </div>
</div>
<!-- Modal de confirmacion generico (reemplaza confirm() nativo, poco fiable en iOS standalone) -->
<div class="overlay" id="modal-confirmar-generico">
  <div class="modal">
    <h2 id="confirmar-generico-titulo">¿Confirmar?</h2>
    <p id="confirmar-generico-mensaje" style="font-size:14px;color:var(--text2);margin-bottom:1.25rem;white-space:pre-line"></p>
    <div class="modal-footer">
      <button onclick="_resolverConfirmarGenerico(false)">Cancelar</button>
      <button class="primary" onclick="_resolverConfirmarGenerico(true)">Continuar</button>
    </div>
  </div>
</div>
</body></html>`);'''

nuevo_limpio = '''    </style></head><body>${generarTicketHTML(ticketActual)}</body></html>`);'''

n1 = src.count(viejo_roto)
if n1 == 1:
    src = src.replace(viejo_roto, nuevo_limpio, 1)
    print("1. imprimirTicket() restaurado correctamente (modales removidos del string)")
elif 'generarTicketHTML(ticketActual)}</body></html>' in src:
    print("1. * imprimirTicket() ya estaba corregido")
else:
    print("1. ERROR: no se encontro el bloque roto exacto. Revisar manualmente.")
    print("   Comparte: grep -n 'generarTicketHTML(ticketActual)' static/pagos.html")

# ================================================================
# 2. Insertar ambos modales como HTML real: despues de </script>
#    pero antes del </body> VERDADERO (el que esta al final absoluto
#    del archivo, identificado de forma unica por este patron de 3 lineas)
# ================================================================
if 'id="pendientes-modal"' not in src or re.search(r'<div class="overlay" id="pendientes-modal">(?!.*`\);)', src, re.DOTALL) is None:
    pass  # se maneja abajo de forma mas simple

viejo_final = '''</script>
</body>
</html>'''

modales_html = '''</script>

<!-- Modal ventas en espera -->
<div class="overlay" id="pendientes-modal">
  <div class="modal">
    <h2>⏸ Ventas en espera</h2>
    <div id="pendientes-lista" style="max-height:340px;overflow-y:auto"></div>
    <div class="modal-footer">
      <button onclick="cerrarPendientes()">Cerrar</button>
    </div>
  </div>
</div>

<!-- Modal de confirmacion generico (reemplaza confirm() nativo, poco fiable en iOS standalone) -->
<div class="overlay" id="modal-confirmar-generico">
  <div class="modal">
    <h2 id="confirmar-generico-titulo">¿Confirmar?</h2>
    <p id="confirmar-generico-mensaje" style="font-size:14px;color:var(--text2);margin-bottom:1.25rem;white-space:pre-line"></p>
    <div class="modal-footer">
      <button onclick="_resolverConfirmarGenerico(false)">Cancelar</button>
      <button class="primary" onclick="_resolverConfirmarGenerico(true)">Continuar</button>
    </div>
  </div>
</div>

</body>
</html>'''

# Solo insertar si los modales ya no estan presentes como HTML real todavia
# (verificamos usando el contexto que rodeaba al bug: si ya se quito el
# bloque roto arriba, aqui los agregamos frescos al final)
if n1 == 1:
    n2 = src.count(viejo_final)
    if n2 == 1:
        src = src.replace(viejo_final, modales_html, 1)
        print("2. Modales insertados correctamente al final del archivo (HTML real)")
    else:
        print("2. ERROR: no se encontro el final exacto del archivo (coincidencias: " + str(n2) + ")")
        print("   Comparte: tail -5 static/pagos.html")
else:
    print("2. Se omite (el paso 1 no se aplico, revisar antes de continuar)")

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
for i, s in enumerate(scripts):
    o, c = s.count('{'), s.count('}')
    print("Script " + str(i+1) + ": {" + str(o) + " }" + str(c) + " " + ("OK" if o==c else "DESBALANCEADO"))

if ok:
    print("\nBalance de llaves OK. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Prueba: el boton de ventas en espera, Y TAMBIEN prueba imprimir un ticket")
    print("(ambos usaban la misma zona rota).")
else:
    print("\nADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
    print("Comparte el resultado completo de este script para revisar mas a fondo.")
