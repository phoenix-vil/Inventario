#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version 2, mas robusta: usa un patron de inicio y fin conocidos, y
reemplaza TODO lo que haya en medio (sin importar espacios en blanco
exactos), en vez de depender de un match literal completo.
Uso: cd ~/inventario/static && python3 fix_modales_v2.py
"""
import os, re

PAGOS = os.path.expanduser('~/inventario/static/pagos.html')
src = open(PAGOS, encoding='utf-8').read()
original = src

# ================================================================
# 1. Quitar TODO lo que este atrapado entre el inicio del template
#    literal de imprimirTicket() y su cierre, sin importar el
#    contenido exacto de en medio (ahi estan los modales atrapados)
# ================================================================
inicio = re.escape('${generarTicketHTML(ticketActual)}')
fin = re.escape('</body></html>`);')
patron = re.compile(inicio + r'.*?' + fin, re.DOTALL)

m = patron.search(src)
if m:
    texto_atrapado = m.group(0)
    src = patron.sub('${generarTicketHTML(ticketActual)}</body></html>`);', src, count=1)
    print("1. imprimirTicket() restaurado (se quito todo el contenido atrapado)")
    print("   Contenido que estaba atrapado (primeras 200 caracteres):")
    print("   " + texto_atrapado[:200].replace('\n', ' | '))
else:
    print("1. * No se encontro contenido atrapado (puede que ya este limpio)")

# ================================================================
# 2. Insertar los modales frescos, correctamente, al final real del
#    archivo (despues de </script>, antes del </body> verdadero)
# ================================================================
if 'id="pendientes-modal"' not in src:
    viejo_final = re.compile(r'</script>\s*</body>\s*</html>\s*$')

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
</html>
'''
    nueva_src, n2 = viejo_final.subn(modales_html, src, count=1)
    if n2 == 1:
        src = nueva_src
        print("2. Modales insertados correctamente al final del archivo (HTML real)")
    else:
        print("2. ERROR: no se encontro el patron final del archivo con regex flexible")
        print("   Comparte: tail -5 static/pagos.html")
else:
    print("2. * Los modales ya existen como HTML real en el archivo, se omite")

# ================================================================
# Guardar y verificar
# ================================================================
if src != original:
    open(PAGOS, 'w', encoding='utf-8').write(src)
    print("\nArchivo guardado.")
else:
    print("\nNo se aplico ningun cambio.")

scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', src, re.DOTALL)
print()
ok = True
for i, s in enumerate(scripts):
    o, c = s.count('{'), s.count('}')
    if o != c: ok = False
    print("Script " + str(i+1) + ": {" + str(o) + " }" + str(c) + " " + ("OK" if o==c else "DESBALANCEADO"))

# Verificar que pendientes-lista ahora existe FUERA de cualquier string JS
# (heuristica simple: debe aparecer despues del ultimo </script> real,
# o en todo caso debe existir en el archivo tal cual)
tiene_modal_real = 'id="pendientes-lista"' in src
print()
print("Contiene pendientes-lista:", tiene_modal_real)

if ok and tiene_modal_real:
    print("\nTodo en orden. Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. Prueba el boton de ventas en espera Y el de imprimir ticket.")
else:
    print("\nADVERTENCIA: algo no quedo bien. NO se reinicio el servicio.")
    print("Comparte toda esta salida para seguir revisando.")
