#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1. Hace que las sesiones expiren despues de 8 horas (backend).
2. Agrega un chequeo periodico en auth.js: valida la sesion cada 20 min
   y recarga la pagina para traer actualizaciones, sin interrumpir si hay
   un modal abierto o un carrito de venta activo con productos.

Uso: cd ~/inventario && python3 expirar_sesion_8h.py
"""
import os, re, ast

BASE = os.path.expanduser('~/inventario')

# ================================================================
# 1. main.py: asegurar que 'timedelta' este importado
# ================================================================
print("1. Verificando import de timedelta en main.py...")
main_path = os.path.join(BASE, 'main.py')
src = open(main_path, encoding='utf-8').read()

m = re.search(r'from datetime import ([^\n]+)', src)
if m and 'timedelta' not in m.group(1):
    nueva_linea = 'from datetime import ' + m.group(1).strip() + ', timedelta'
    src = src.replace(m.group(0), nueva_linea, 1)
    print("   OK timedelta agregado")
elif m:
    print("   * timedelta ya estaba importado")
else:
    print("   ADVERTENCIA: no se encontro 'from datetime import ...'")

# ================================================================
# 2. main.py: agregar expiracion de 8 horas en get_sesion()
# ================================================================
print("2. Agregando expiracion de 8 horas a get_sesion()...")

viejo = '''def get_sesion(authorization: Optional[str], db: Session) -> Optional[Sesion]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    return db.query(Sesion).filter(Sesion.token == token).first()'''

nuevo = '''def get_sesion(authorization: Optional[str], db: Session) -> Optional[Sesion]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    s = db.query(Sesion).filter(Sesion.token == token).first()
    if not s:
        return None
    if datetime.utcnow() - s.creado_en > timedelta(hours=8):
        db.delete(s)
        db.commit()
        return None
    return s'''

n = src.count(viejo)
if n == 1:
    src = src.replace(viejo, nuevo, 1)
    print("   OK expiracion de 8 horas agregada")
    open(main_path, 'w', encoding='utf-8').write(src)
elif n == 0:
    print("   ERROR: no se encontro el texto exacto de get_sesion(). No se modifico nada.")
else:
    print("   ERROR: se encontro mas de una coincidencia (" + str(n) + "). Revisar manualmente.")

# Verificar sintaxis
try:
    ast.parse(open(main_path, encoding='utf-8').read())
    print("   Sintaxis de main.py: OK")
    main_ok = True
except SyntaxError as e:
    print("   ERROR de sintaxis en main.py, linea " + str(e.lineno) + ": " + str(e.text))
    main_ok = False

# ================================================================
# 3. auth.js: chequeo periodico de sesion + auto-recarga
# ================================================================
print("3. Agregando chequeo periodico a auth.js...")
auth_path = os.path.join(BASE, 'static', 'auth.js')
src = open(auth_path, encoding='utf-8').read()

if 'Chequeo periodico de sesion' in src:
    print("   * Ya existia, se omite")
else:
    bloque = '''

// ─── Chequeo periodico de sesion + auto-actualizacion ──────────────────────
// Cada 20 minutos: valida que la sesion siga activa (si expiro, manda a login)
// y recarga la pagina para traer actualizaciones, salvo que haya un modal
// abierto o un carrito de venta con productos (para no interrumpir al usuario).
(function () {
  const INTERVALO_MIN = 20;
  setInterval(async () => {
    const s = getSesion();
    if (!s || !s.token) return;

    try {
      const r = await fetch('/api/sesion', { headers: { 'Authorization': 'Bearer ' + s.token } });
      if (r.status === 401) {
        localStorage.removeItem('sesion');
        location.href = '/login';
        return;
      }
    } catch (e) {
      return; // sin conexion por ahora, se reintenta en el siguiente ciclo
    }

    if (document.querySelector('.overlay.open')) return;
    if (typeof carrito !== 'undefined' && Array.isArray(carrito) && carrito.length > 0) return;

    location.reload();
  }, INTERVALO_MIN * 60 * 1000);
})();
'''
    src = src.rstrip('\n') + bloque
    open(auth_path, 'w', encoding='utf-8').write(src)
    print("   OK chequeo periodico agregado")

# ================================================================
# Resumen y reinicio
# ================================================================
print()
print("=" * 55)
if main_ok:
    print("Reiniciando el servicio...")
    os.system("sudo systemctl restart inventario")
    print()
    print("Listo:")
    print("  - Las sesiones expiran a las 8 horas de haber iniciado sesion")
    print("  - Cada 20 min se valida la sesion y se recarga la pagina si no hay")
    print("    modales abiertos ni carrito activo con productos")
else:
    print("ADVERTENCIA: no se reinicio el servicio por el error de sintaxis de arriba.")
