# Inventario — servidor personal

## Archivos del proyecto

```
inventario/
├── main.py          # API FastAPI (todos los endpoints)
├── database.py      # Modelos SQLite
├── schemas.py       # Validación Pydantic
├── install.sh       # Instalador automático
└── static/
    └── index.html   # App web (se abre en el navegador)
```

## Instalación rápida

```bash
chmod +x install.sh
./install.sh
```

## Uso manual (sin systemd)

```bash
pip install fastapi uvicorn sqlalchemy pydantic --break-system-packages
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Acceso desde tus dispositivos

Desde cualquier dispositivo con Tailscale conectado:

```
http://<ip-tailscale-de-tu-servidor>:8000
```

La IP Tailscale de tu servidor la ves con:
```bash
tailscale ip -4
```

## Endpoints de la API

| Método | Ruta                         | Descripción              |
|--------|------------------------------|--------------------------|
| GET    | /api/productos               | Listar (con filtros)     |
| POST   | /api/productos               | Crear producto           |
| PATCH  | /api/productos/{id}          | Editar producto          |
| DELETE | /api/productos/{id}          | Eliminar                 |
| POST   | /api/productos/{id}/stock    | Ajustar stock (+/-)      |
| GET    | /api/precio/{nombre}         | Consulta rápida de precio|
| GET    | /api/resumen                 | Estadísticas del negocio |
| GET    | /api/categorias              | Lista de categorías      |
| GET    | /docs                        | Documentación interactiva|

## Comandos útiles

```bash
# Ver si el servicio está corriendo
systemctl status inventario

# Ver logs en tiempo real
journalctl -u inventario -f

# Reiniciar
sudo systemctl restart inventario

# Hacer backup de la base de datos
cp ~/inventario/inventario.db ~/inventario_backup_$(date +%Y%m%d).db
```
# Inventario
