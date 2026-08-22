"""Agente del cajón de dinero.

Corre en la PC de Windows donde está conectada por USB la impresora Xprinter
(el cajón EC-CD-50M cuelga de ella por el cable RJ11 de atrás). Escucha en
127.0.0.1 y, cuando pagos.html le pide "abre el cajón" al confirmar un cobro
en efectivo, le manda a la impresora el byte de ESC/POS que dispara el pulso.

Por qué hace falta este programa aparte: el ticket se imprime con el diálogo
normal de Windows (window.print() del navegador), que solo sabe mandar la hoja
ya dibujada — nunca ese byte de control. Hay que hablarle a la impresora por
otra vía, y el navegador no puede hacerlo directo por razones de seguridad;
este agente es el puente.

No toca el driver ni la cola de impresión normal: usa la API de impresión de
Windows en modo RAW, el mismo mecanismo por el que ya imprime tickets, así que
no hay ningún cambio para lo que ya funciona.

Requiere:  pip install pywin32
Ejecutar con pythonw.exe (sin ventana de consola) para dejarlo en segundo
plano; ver instalar.bat.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import win32print
except ImportError:
    print("Falta pywin32. Instálalo con:  pip install pywin32")
    sys.exit(1)

PUERTO = 8788

# El nombre EXACTO que Windows le puso a la impresora al instalarla —se ve en
# Configuración > Impresoras y escáneres. Ajusta esta línea si el tuyo es
# distinto (ver README de esta carpeta para cómo comprobarlo).
NOMBRE_IMPRESORA = "XP-58IIH"

# ESC p m t1 t2 — "generar pulso" de ESC/POS. m=0 es el pin 2 del RJ11, que es
# donde casi todos los cajones (incluido el EC-CD-50M) esperan la señal. Si no
# abre, el README explica cómo probar con m=1 (pin 5).
PULSO_ABRIR_CAJON = b"\x1b\x70\x00\x19\xfa"


def abrir_cajon():
    h = win32print.OpenPrinter(NOMBRE_IMPRESORA)
    try:
        # Tipo de trabajo "RAW": los bytes se mandan tal cual a la impresora,
        # sin que Windows intente interpretarlos como un documento.
        job = win32print.StartDocPrinter(h, 1, ("Abrir cajon", None, "RAW"))
        try:
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, PULSO_ABRIR_CAJON)
            win32print.EndPagePrinter(h)
        finally:
            win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        # pagos.html se sirve desde el dominio de Tailscale (otro origen que
        # 127.0.0.1), así que el navegador exige estas cabeceras para permitir
        # la petición.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _responder(self, codigo, cuerpo):
        self.send_response(codigo)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(cuerpo).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Para probar desde el navegador de la propia PC: abrir
        # http://127.0.0.1:8788/ debe responder esto si el agente está vivo.
        if self.path == "/":
            self._responder(200, {"agente": "cajon de dinero", "estado": "activo"})
        else:
            self._responder(404, {"ok": False, "error": "ruta no encontrada"})

    def do_POST(self):
        if self.path != "/abrir-cajon":
            self._responder(404, {"ok": False, "error": "ruta no encontrada"})
            return
        try:
            abrir_cajon()
            self._responder(200, {"ok": True})
        except Exception as e:
            self._responder(500, {"ok": False, "error": str(e)})

    def log_message(self, formato, *args):
        pass  # sin logs en consola: corre oculto con pythonw.exe


if __name__ == "__main__":
    servidor = HTTPServer(("127.0.0.1", PUERTO), Handler)
    print("Agente del cajón escuchando en http://127.0.0.1:%d" % PUERTO)
    print("Impresora configurada: %r" % NOMBRE_IMPRESORA)
    servidor.serve_forever()
