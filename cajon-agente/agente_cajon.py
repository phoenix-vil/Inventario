"""Agente del punto de venta: abre el cajón de dinero e imprime el ticket
directo a la impresora, sin el diálogo de impresión de Windows.

Corre en la PC de Windows donde está conectada por USB la impresora Xprinter
(el cajón EC-CD-50M cuelga de ella por el cable RJ11 de atrás). Escucha en
127.0.0.1 y pagos.html le pide dos cosas, cada una con su propia ruta:

  - Al confirmar un cobro en efectivo: que abra el cajón.
  - Al confirmar cualquier venta: que imprima el ticket ella misma, sin pasar
    por el diálogo de impresión del navegador.

Por qué hace falta este programa aparte: tanto el ticket (con window.print())
como el cajón necesitan hablarle a la impresora por comandos ESC/POS que ese
diálogo nunca manda —solo sabe entregarle una hoja ya dibujada—. Hay que
hablarle por otra vía, y el navegador no puede hacerlo directo sin cambiarle
el driver a la impresora (lo que rompería la impresión normal); este agente es
el puente.

El ticket se imprime como IMAGEN, no como texto: pagos.html genera exactamente
el mismo dibujo que ya usa para compartir por WhatsApp o descargar en PDF (con
el logo de la tienda y el mismo diseño) y manda ese PNG tal cual; este agente
solo lo convierte a blanco y negro puro y lo empaqueta en el comando de imagen
de la impresora. Es más lento que imprimir texto plano y el detalle fino
(letras chicas) pierde algo de nitidez al pasar por blanco y negro, pero es
la única forma de que el papel se vea igual al de pantalla.

No toca el driver ni la cola de impresión normal: usa la API de impresión de
Windows en modo RAW, el mismo mecanismo por el que ya imprimía tickets, así
que no hay ningún cambio para lo que ya funciona — y si este agente no está
corriendo, pagos.html cae solo de vuelta al diálogo de impresión de siempre.

Requiere:  pip install -r requirements.txt   (pywin32 y Pillow)
Ejecutar con pythonw.exe (sin ventana de consola) para dejarlo en segundo
plano; ver iniciar_agente.vbs y el README de esta carpeta.
"""
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import win32print
except ImportError:
    print("Falta pywin32. Instálalo con:  pip install -r requirements.txt")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Falta Pillow. Instálalo con:  pip install -r requirements.txt")
    sys.exit(1)

PUERTO = 8788

# El nombre EXACTO que Windows le puso a la impresora al instalarla —se ve en
# Configuración > Impresoras y escáneres. Ajusta esta línea si el tuyo es
# distinto (ver README de esta carpeta para cómo comprobarlo).
NOMBRE_IMPRESORA = "XP-58IIH"

# Ancho de impresión de esta impresora en puntos: 58mm de papel a 203dpi
# (8 puntos por mm, la densidad estándar de estas térmicas) dan ~384 puntos
# útiles. Si el ticket sale recortado por un lado o muy angosto con margen de
# sobra, este es el número a ajustar.
ANCHO_IMPRESORA_PX = 384

# ESC p m t1 t2 — "generar pulso" de ESC/POS. m=0 es el pin 2 del RJ11, que es
# donde casi todos los cajones (incluido el EC-CD-50M) esperan la señal. Si no
# abre, el README explica cómo probar con m=1 (pin 5).
PULSO_ABRIR_CAJON = b"\x1b\x70\x00\x19\xfa"

# GS V m — corte de papel, en su forma clásica de un solo parámetro (la más
# compatible con impresoras económicas/genéricas; hay una variante de dos
# parámetros con avance incluido que no todos los modelos entienden igual).
# m=0x00 corte total, m=0x01 corte parcial (deja una pestaña de papel sin
# cortar). Si con ninguno de los dos corta, no es un problema de software:
# revisa si la impresora tiene un DIP switch físico de "Cutter" apagado
# (suele estar bajo una tapa lateral o inferior), o si este modelo en
# particular no trae cuchilla instalada —los hay con y sin ella bajo el mismo
# nombre— y el papel se corta a mano contra el borde dentado de la tapa.
CORTE_PAPEL = b"\n\n\n\x1d\x56\x00"  # alimenta unas líneas y corta (total)


def imagen_a_comando_raster(datos_png: bytes) -> bytes:
    """Convierte el PNG del ticket (el mismo que genera pagos.html para
    compartir por WhatsApp o descargar) al comando ESC/POS de imagen raster
    (GS v 0), listo para mandarse tal cual a la impresora.

    Ojo con la convención de bits, que es la parte fácil de arruinar aquí:
    Pillow empaqueta 1=blanco/0=negro en modo "1", pero ESC/POS espera lo
    contrario (1=imprimir/negro, 0=no imprimir/blanco) — así que hay que
    invertir cada byte, o el ticket saldría con los colores cambiados."""
    img = Image.open(io.BytesIO(datos_png))

    # Sin esto, cualquier transparencia del PNG (por ejemplo alrededor del
    # logo) se convertiría en negro sólido al pasar a blanco y negro.
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        fondo = Image.new("RGB", img.size, "white")
        fondo.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = fondo
    else:
        img = img.convert("RGB")

    if img.width != ANCHO_IMPRESORA_PX:
        alto_nuevo = round(img.height * ANCHO_IMPRESORA_PX / img.width)
        img = img.resize((ANCHO_IMPRESORA_PX, alto_nuevo), Image.LANCZOS)

    # Blanco y negro puro, con difuminado (Floyd-Steinberg, el que usa Pillow
    # por defecto): es lo que permite que el logo —que trae degradados de
    # color— se siga distinguiendo en una impresora que solo pinta o no pinta.
    bn = img.convert("1")
    ancho_bytes = (bn.width + 7) // 8
    datos = bytes(b ^ 0xFF for b in bn.tobytes())

    xL, xH = ancho_bytes & 0xFF, (ancho_bytes >> 8) & 0xFF
    yL, yH = bn.height & 0xFF, (bn.height >> 8) & 0xFF
    return b"\x1d\x76\x30\x00" + bytes([xL, xH, yL, yH]) + datos


def _mandar_a_impresora(nombre_trabajo, datos_raw):
    h = win32print.OpenPrinter(NOMBRE_IMPRESORA)
    try:
        # Tipo de trabajo "RAW": los bytes se mandan tal cual a la impresora,
        # sin que Windows intente interpretarlos como un documento.
        win32print.StartDocPrinter(h, 1, (nombre_trabajo, None, "RAW"))
        try:
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, datos_raw)
            win32print.EndPagePrinter(h)
        finally:
            win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)


def abrir_cajon():
    _mandar_a_impresora("Abrir cajon", PULSO_ABRIR_CAJON)


def imprimir_ticket(datos_png: bytes):
    comando = imagen_a_comando_raster(datos_png)
    _mandar_a_impresora("Ticket de venta", comando + CORTE_PAPEL)


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        # pagos.html se sirve desde el dominio de Tailscale (otro origen que
        # 127.0.0.1), así que el navegador exige estas cabeceras para permitir
        # la petición. La última (Private-Network) es aparte de CORS: Chrome y
        # Edge, desde que existe "Private Network Access", bloquean en
        # silencio —sin ningún error visible para quien usa la app, solo un
        # aviso en la consola del navegador— que una página cargada desde
        # una dirección de internet (el dominio de Tailscale) llame a algo en
        # localhost/la red local, salvo que el propio servidor lo autorice
        # explícito. curl no aplica esta regla —por eso las pruebas manuales
        # con curl.exe sí funcionaban aunque la app no disparara nada—.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

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
            self._responder(200, {"agente": "punto de venta", "estado": "activo"})
        else:
            self._responder(404, {"ok": False, "error": "ruta no encontrada"})

    def do_POST(self):
        if self.path == "/abrir-cajon":
            try:
                abrir_cajon()
                self._responder(200, {"ok": True})
            except Exception as e:
                self._responder(500, {"ok": False, "error": str(e)})
            return
        if self.path == "/imprimir-ticket":
            try:
                largo = int(self.headers.get("Content-Length", 0))
                datos_png = self.rfile.read(largo) if largo else b""
                if not datos_png:
                    raise ValueError("no llegó ninguna imagen en el cuerpo de la petición")
                imprimir_ticket(datos_png)
                self._responder(200, {"ok": True})
            except Exception as e:
                self._responder(500, {"ok": False, "error": str(e)})
            return
        self._responder(404, {"ok": False, "error": "ruta no encontrada"})

    def log_message(self, formato, *args):
        pass  # sin logs en consola: corre oculto con pythonw.exe


if __name__ == "__main__":
    servidor = HTTPServer(("127.0.0.1", PUERTO), Handler)
    print("Agente del punto de venta escuchando en http://127.0.0.1:%d" % PUERTO)
    print("Impresora configurada: %r" % NOMBRE_IMPRESORA)
    servidor.serve_forever()
