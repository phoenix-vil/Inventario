# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

El proyecto, sus comentarios y su interfaz están en español. Escribe código, comentarios y mensajes de commit en español.

## Qué es

Punto de venta + inventario multi-sucursal para un negocio real, con datos de producción en vivo (~2 800 productos, ventas reales). FastAPI + SQLAlchemy + SQLite, servido por systemd detrás de Tailscale. El frontend es HTML/JS puro sin build ni npm.

## Dos entornos en la misma máquina

| Ruta | Puerto | Qué es |
|------|--------|--------|
| `~/inventario` | 8000 | **Producción.** Servicio systemd `inventario`. Datos reales. |
| `~/inventario-qa` | 8001 | Pruebas. uvicorn lanzado a mano. Copia del proyecto con sus propios scripts `qa_*.py`. |

El flujo normal es: desarrollar y probar en `~/inventario-qa` (:8001), y solo entonces portar el cambio a `~/inventario`. No edites producción directamente sin decirlo.

```bash
# Producción
sudo systemctl restart inventario     # aplicar cambios de main.py/database.py
systemctl status inventario
journalctl -u inventario -f           # logs

# QA (se lanza a mano desde ~/inventario-qa)
uvicorn main:app --host 0.0.0.0 --port 8001
```

Los cambios en `static/*.html` no requieren reinicio; los de Python sí.

## Antes de tocar nada: respaldo

La convención del proyecto es crear una carpeta de respaldo con fecha antes de cualquier cambio grande, en `~/` (no dentro del repo):

```bash
cp -r ~/inventario ~/respaldo-<tema>-$(date +%Y%m%d-%H%M)
cp ~/inventario/inventario.db ~/inventario/inventario.db.backup-$(date +%Y%m%d-%H%M)
```

Ya existen varias (`respaldo-pre-devoluciones-*`, `respaldo-pre-pwa-*`, …). Sigue el patrón.

No hay tests. La verificación es manual contra :8001 y contra `/docs` (Swagger de FastAPI).

## Arquitectura

Tres archivos llevan todo el backend:

- **`main.py`** (~80 KB, 76 endpoints) — toda la API en un solo archivo, sin routers. Las secciones se separan con comentarios `# ─── Título ───`.
- **`database.py`** — modelos SQLAlchemy, hashing de contraseñas (`hash_password` / `verificar_password` con salt, hashlib) y `init_db()`.
- **`schemas.py`** — modelos Pydantic de entrada.

Modelos: `Producto`, `StockSucursal`, `Usuario`, `Venta`, `Cotizacion`, `Sucursal`, `Sesion`, `VentaPendiente`, `Gasto`, `Cliente`, `PagoCredito`.

### Migraciones: no las hay — cuidado

`init_db()` solo llama a `Base.metadata.create_all()`, que **crea tablas nuevas pero nunca añade columnas a tablas existentes**. Si agregas una columna a un modelo, la base de producción no la tendrá y las consultas fallarán en runtime.

Al añadir una columna hay que hacer las dos cosas:
1. declararla en el modelo de `database.py`, y
2. ejecutar el `ALTER TABLE` correspondiente sobre `inventario.db` (los scripts `qa_devoluciones_backend.py`, `qa_agregar_transferencia.py` y `qa_cotizacion_marcar_vendida.py` en `~/inventario-qa` muestran el patrón, incluyendo cómo detectar si la columna ya existe).

### Autenticación

Sesiones por token en la tabla `sesiones`, con caducidad de **8 horas**. El cliente guarda `{token, usuario, rol, sucursal}` en `localStorage` bajo la clave `sesion` y lo manda como `Authorization: Bearer <token>`.

En el backend, protege cada endpoint con una de las dependencias de `main.py`:
- `requerir_sesion` → cualquier usuario autenticado
- `requerir_gerente` → solo `rol == "gerente"` (el otro rol es operador)

La sesión guarda la **sucursal** con la que se hizo login; muchos endpoints filtran por ella. Usuario semilla: `admin` / `admin123`.

### Frontend

Cada pantalla es un `.html` autocontenido en `static/` (HTML + CSS + JS inline en el mismo archivo), servido por una ruta `FileResponse` en `main.py` (`/`, `/login`, `/pagos`, `/historial`, `/devoluciones`, `/cotizaciones`, `/clientes`, `/gastos`, `/dashboard`, `/inventario-sucursales`, `/sucursales`, `/usuarios`, `/precios`). Es una PWA (`manifest.json`), usada principalmente desde iPhone en modo standalone.

Lo único compartido entre páginas es **`static/auth.js`** y `static/modern.css`. Desde JS usa siempre los helpers de `auth.js`, no `fetch` pelado:

- `authFetch(url, opts, skipAuthRedirect)` — añade el token y redirige a `/login` en un 401. Pasa `skipAuthRedirect = true` cuando el endpoint valida *otras* credenciales (p. ej. `/api/pos/autorizar`, donde un 401 significa "PIN de gerente incorrecto", no "tu sesión caducó").
- `requireAuth()` / `requireGerente()` / `esGerente()` — control de acceso al cargar la página.
- `confirmarPersonalizado(msg, titulo)` / `promptPersonalizado(msg, default, titulo)` — **usa estos en lugar de `confirm()` y `prompt()` nativos**, que no funcionan de forma fiable en iOS standalone. Devuelven Promises.

`auth.js` también recarga la página cada 20 minutos para repartir actualizaciones, saltándose la recarga si hay un `.overlay.open` o si la variable global `carrito` tiene productos. Si añades un modal, dale la clase `overlay` y `open` para no interrumpir al usuario.

## Los scripts sueltos `fix_*.py` / `qa_*.py` / `agregar_*.py`

Las ~50 decenas de scripts en la raíz y en `static/` **no son parte de la aplicación**. Son parches de un solo uso, ya aplicados, que modifican `main.py` y los HTML por búsqueda-y-reemplazo de cadenas literales. Sirven como historial de cambios y como referencia de cómo se hizo algo, pero:

- No los vuelvas a ejecutar (algunos son idempotentes y otros no).
- No los tomes como fuente de verdad del estado actual: lee `main.py` y los HTML.
- Para un cambio nuevo, edita los archivos directamente con Edit. No hace falta escribir un script de parche nuevo salvo que el usuario lo pida.

## Control de versiones

Un solo repositorio (`origin` = `github.com:phoenix-vil/Inventario`) con una rama por entorno:

| Carpeta | Rama | Entorno |
|---------|------|---------|
| `~/inventario` | `main` | Producción (:8000). Solo recibe merges desde `qa`. |
| `~/inventario-qa` | `qa` | Pruebas (:8001). Aquí se desarrolla. |

`inventario.db` **no se versiona** (está en `.gitignore`, junto con `__pycache__/`, `.serper_key`, `serper_log.csv` y los `.zip`). Cada entorno conserva su propia base: hacer merge o cambiar de rama nunca toca los datos.

### Flujo para un cambio

```bash
# 1. Desarrollar y probar en QA
cd ~/inventario-qa                    # rama qa
# ...editar, probar contra :8001...
git add -A && git commit -m "Descripción en español"
git push origin qa

# 2. Pasar a producción, ya probado
cd ~/inventario                       # rama main
git merge qa
sudo systemctl restart inventario
# ...verificar :8000...
git tag -a v1.1.0 -m "Qué incluye esta versión"
git push origin main --follow-tags
```

Las etiquetas `vX.Y.Z` en `main` marcan qué versión corre en producción. Para saberlo en cualquier momento: `git describe --tags`. Para volver a una versión anterior si algo sale mal: `git revert <commit>` (preferible) o `git checkout v1.0.0 -- <archivo>` para un archivo suelto, y reiniciar el servicio.

Sigue haciendo el respaldo con fecha antes de cambios grandes: git versiona el código, pero no `inventario.db`.
