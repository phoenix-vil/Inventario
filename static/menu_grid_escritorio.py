#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agrega un diseno en cuadricula (recuadros) para el menu principal SOLO
en pantallas de escritorio (min-width:1024px). En movil/tablet se queda
exactamente igual (la lista vertical que ya existe).
Uso: cd ~/inventario/static && python3 menu_grid_escritorio.py
"""
import os, re, time

MENU = os.path.expanduser('~/inventario/static/menu.html')
src = open(MENU, encoding='utf-8').read()
original = src

# ================================================================
# Insertar la media query de escritorio justo despues de .arrow{...}
# ================================================================
viejo = '.arrow{color:var(--text2);font-size:22px}'

nuevo = '''.arrow{color:var(--text2);font-size:22px}

/* Version de escritorio: recuadros en cuadricula en vez de lista.
   Movil y tablet (menos de 1024px) se quedan con el diseno de lista sin cambios. */
@media(min-width:1024px){
  .menu{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    max-width:1100px;
    gap:18px;
  }
  .menu-btn{
    flex-direction:column;
    align-items:center;
    text-align:center;
    padding:2rem 1.5rem;
    gap:14px;
  }
  .menu-btn .icon{
    width:64px;
    height:64px;
    font-size:32px;
  }
  .menu-text{
    flex:none;
  }
  .arrow{
    display:none;
  }
}'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("OK: media query de escritorio agregada (recuadros en cuadricula)")
elif 'min-width:1024px' in src:
    print("* Ya existia, se omite")
else:
    print("ERROR: no se encontro la regla .arrow exacta")

if src != original:
    open(MENU, 'w', encoding='utf-8').write(src)
    print("Archivo guardado.")

# Actualizar version de cache-busting de modern.css tambien (por si acaso)
# y verificar balance de llaves antes de reiniciar
import re as re2
llaves_ok = src.count('{') == src.count('}')
print()
print("Balance de llaves en el archivo:", "OK" if llaves_ok else "DESBALANCEADO")

print()
print("=" * 55)
if llaves_ok:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print("Listo. En pantallas de escritorio (1024px+) el menu se vera en recuadros.")
    print("En movil/tablet se queda exactamente como estaba.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
