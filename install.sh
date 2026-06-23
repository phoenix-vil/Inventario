#!/bin/bash
# install.sh — instala y configura el servidor de inventario en Ubuntu

set -e

echo "=== Inventario: instalación ==="

# 1. Dependencias Python
echo "[1/4] Instalando dependencias..."
pip install fastapi uvicorn sqlalchemy pydantic --break-system-packages -q

# 2. Copiar archivos al directorio de destino
DEST="$HOME/inventario"
echo "[2/4] Copiando archivos a $DEST..."
mkdir -p "$DEST/static"
cp main.py database.py schemas.py "$DEST/"
cp static/index.html "$DEST/static/"

# 3. Crear servicio systemd para que arranque solo con el servidor
echo "[3/4] Creando servicio systemd..."
SERVICE_FILE="/etc/systemd/system/inventario.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Inventario - servidor de productos
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DEST
ExecStart=$(which uvicorn) main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable inventario
sudo systemctl restart inventario

# 4. Mostrar info
echo ""
echo "=== ¡Listo! ==="
echo ""
echo "  Servicio:   systemctl status inventario"
echo "  Logs:       journalctl -u inventario -f"
echo ""
# Obtener IP de Tailscale si está disponible
TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
if [ -n "$TS_IP" ]; then
  echo "  App web:    http://$TS_IP:8000"
  echo "  API docs:   http://$TS_IP:8000/docs"
else
  echo "  App web:    http://<ip-tailscale>:8000"
  echo "  (Tailscale no detectado — instálalo y vuelve a verificar)"
fi
echo ""
