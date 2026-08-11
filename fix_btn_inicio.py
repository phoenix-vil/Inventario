#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reemplaza el logo completo (con texto "enterprises") en los botones de
"regresar al inicio" por SOLO el simbolo de la luna, con fondo transparente
que se invierte automaticamente a blanco en modo oscuro para buen contraste.
NO toca el logo grande de login.html ni el del header de menu.html.
Uso: cd ~/inventario && python3 fix_btn_inicio.py
"""
import os, re, base64

STATIC = os.path.expanduser('~/inventario/static')

ICON_NAV_B64 = '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'

# ================================================================
# 1. Guardar el icono de navegacion (transparente, solo la luna)
# ================================================================
print("1. Guardando static/icon-nav.png...")
icon_path = os.path.join(STATIC, 'icon-nav.png')
with open(icon_path, 'wb') as f:
    f.write(base64.b64decode(ICON_NAV_B64))
print("   OK icon-nav.png guardado (" + str(os.path.getsize(icon_path)) + " bytes)")

# ================================================================
# 2. Agregar la regla CSS de inversion en modo oscuro a modern.css
#    (se aplica automaticamente en todas las paginas que lo usan)
# ================================================================
print("2. Agregando regla de contraste en modo oscuro a modern.css...")
modern_path = os.path.join(STATIC, 'modern.css')
msrc = open(modern_path, encoding='utf-8').read()

if '.nav-icon' not in msrc:
    regla = '''

/* Icono de "regresar al inicio": solo el simbolo, se invierte en modo oscuro para contraste */
.nav-icon{display:block}
@media(prefers-color-scheme:dark){
  .nav-icon{filter:invert(1)}
}
'''
    msrc = msrc.rstrip('\n') + regla
    open(modern_path, 'w', encoding='utf-8').write(msrc)
    print("   OK regla .nav-icon agregada a modern.css")
else:
    print("   * La regla .nav-icon ya existia, se omite")

# ================================================================
# 3. Reemplazar el <img> del logo completo en los botones btn-inicio
#    (identificado por el estilo height:36px, unico de estos botones)
#    por el icono nuevo, en todas las paginas internas
# ================================================================
print("3. Actualizando el icono en los botones 'Inicio'...")
paginas = ['index.html', 'precios.html', 'pagos.html', 'historial.html',
           'usuarios.html', 'inv_sucursales.html']
total = 0

patron = re.compile(
    r'<img src="/static/logo\.png(?:\?v=\d+)?"[^>]*style="height:36px;width:auto;display:block"[^>]*>'
)
nuevo_img = '<img src="/static/icon-nav.png" alt="Inicio" class="nav-icon" style="height:32px;width:32px">'

for pagina in paginas:
    ruta = os.path.join(STATIC, pagina)
    if not os.path.exists(ruta):
        print("   - " + pagina + ": no encontrado, se omite")
        continue
    src = open(ruta, encoding='utf-8').read()
    original = src

    nueva, n = patron.subn(nuevo_img, src)
    if n > 0:
        open(ruta, 'w', encoding='utf-8').write(nueva)
        total += n
        print("   OK " + pagina + ": icono reemplazado")
    else:
        print("   * " + pagina + ": no se encontro el patron esperado (revisar manualmente)")

print("   Total: " + str(total) + " botones actualizados")

print()
print("=" * 50)
print("Reiniciando el servicio...")
os.system("sudo systemctl restart inventario")
print("Listo. Refresca cualquier pagina interna (Inventario, Precios, Pagos, etc.)")
print("con Cmd+Shift+R / Ctrl+Shift+R. El boton de Inicio ahora debe mostrar")
print("solo el simbolo de la luna, visible tanto en modo claro como oscuro.")
