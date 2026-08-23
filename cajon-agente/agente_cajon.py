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

No toca el driver ni la cola de impresión normal: usa la API de impresión de
Windows en modo RAW, el mismo mecanismo por el que ya imprimía tickets, así
que no hay ningún cambio para lo que ya funciona — y si este agente no está
corriendo, pagos.html cae solo de vuelta al diálogo de impresión de siempre.

Requiere:  pip install pywin32
Ejecutar con pythonw.exe (sin ventana de consola) para dejarlo en segundo
plano; ver iniciar_agente.vbs y el README de esta carpeta.
"""
import json
import sys
import textwrap
from datetime import datetime
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

# Caracteres por línea con la fuente normal en papel de 58mm. Es el valor
# típico de esta impresora; si el ticket sale con líneas cortadas de más o
# con mucho espacio sobrante a la derecha, ajusta este número (30-33 es el
# rango habitual) y no hace falta tocar nada más.
ANCHO_TICKET = 32

# ESC p m t1 t2 — "generar pulso" de ESC/POS. m=0 es el pin 2 del RJ11, que es
# donde casi todos los cajones (incluido el EC-CD-50M) esperan la señal. Si no
# abre, el README explica cómo probar con m=1 (pin 5).
PULSO_ABRIR_CAJON = b"\x1b\x70\x00\x19\xfa"

# ─── Comandos ESC/POS usados para armar el ticket ───────────────────────────
ESC_INICIALIZAR = b"\x1b\x40"
ESC_CENTRAR = b"\x1b\x61\x01"
ESC_IZQUIERDA = b"\x1b\x61\x00"
ESC_NEGRITA_ON = b"\x1b\x45\x01"
ESC_NEGRITA_OFF = b"\x1b\x45\x00"
ESC_DOBLE_ON = b"\x1d\x21\x11"   # doble ancho y alto, para el total
ESC_DOBLE_OFF = b"\x1d\x21\x00"
ESC_CODEPAGE_CP850 = b"\x1b\x74\x02"  # para que á/é/í/ó/ú/ñ salgan bien
CORTE_PAPEL = b"\n\n\n\x1d\x56\x42\x00"  # alimenta unas líneas y corta


def money(n):
    """Mismo formato que money() en pagos.html: "$1,234.56"."""
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        n = 0.0
    return "${:,.2f}".format(n)


def _codificar(texto):
    # Las térmicas no hablan UTF-8: reemplaza lo que CP850 no tenga en vez de
    # reventar con una excepción a media impresión.
    return texto.encode("cp850", errors="replace")


def _linea(izquierda, derecha, ancho=ANCHO_TICKET):
    """Une dos textos en una línea de `ancho` columnas, izquierda pegada al
    margen y derecha pegada al borde derecho. Si no caben juntos, el texto de
    la izquierda se reparte en varias líneas y el de la derecha queda solo en
    la última —igual que hace cualquier ticket de tienda con un nombre largo
    de producto."""
    espacio = ancho - len(izquierda) - len(derecha)
    if espacio >= 1:
        return izquierda + (" " * espacio) + derecha
    renglones = textwrap.wrap(izquierda, ancho) or [""]
    ultimo = renglones[-1]
    espacio_ultimo = ancho - len(ultimo) - len(derecha)
    if espacio_ultimo >= 1:
        renglones[-1] = ultimo + (" " * espacio_ultimo) + derecha
    else:
        renglones.append(derecha.rjust(ancho))
    return "\n".join(renglones)


def _fecha_legible(iso):
    try:
        limpio = iso.replace("Z", "")
        if "." in limpio:
            limpio = limpio.split(".")[0]
        dt = datetime.fromisoformat(limpio)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso or ""


def construir_ticket_escpos(v):
    """Arma los bytes del ticket a partir de los mismos datos que ya dibuja
    generarTicketHTML() en pagos.html —incluida su misma forma un poco rara
    de mostrar el descuento por artículo (ver comentario más abajo)—, para que
    el ticket impreso diga siempre lo mismo que el que se ve en pantalla."""
    raya = "-" * ANCHO_TICKET
    partes = [ESC_INICIALIZAR, ESC_CODEPAGE_CP850]

    def linea(txt=""):
        partes.append(_codificar(txt + "\n"))

    partes.append(ESC_CENTRAR)
    partes.append(ESC_NEGRITA_ON)
    linea(v.get("encabezado") or "Only Enterprises")
    partes.append(ESC_NEGRITA_OFF)
    if v.get("sucursal"):
        linea("Sucursal " + v["sucursal"])
    linea("Ticket de venta #%s" % v.get("id", ""))
    linea(_fecha_legible(v.get("fecha")))
    if v.get("operador"):
        linea("Operador: " + v["operador"])
    partes.append(ESC_IZQUIERDA)
    linea(raya)

    for it in v.get("detalle") or []:
        cantidad = it.get("cantidad", 0)
        cant_txt = ("%gx" % cantidad) if float(cantidad).is_integer() else ("%.3fkg" % cantidad)
        nombre = "%s %s" % (cant_txt, it.get("nombre", ""))
        precio_original = it.get("precio_original")
        precio_unitario = it.get("precio_unitario", 0)
        importe = it.get("importe", 0)
        # Igual que en generarTicketHTML(): si hay descuento por artículo, la
        # primera línea es el importe SIN descuento y la segunda dice
        # "Descuento (X%)" pero con el importe YA descontado —no el monto
        # restado—; se replica tal cual para que pantalla y papel coincidan.
        if precio_original is not None and precio_original > precio_unitario:
            importe_original = precio_original * cantidad
            pct = round((1 - precio_unitario / precio_original) * 100)
            linea(_linea(nombre, money(importe_original)))
            linea(_linea("Descuento (%d%%)" % pct, money(importe)))
        else:
            linea(_linea(nombre, money(importe)))
    linea(raya)

    if (v.get("descuento_extra_pct") or 0) > 0:
        pct = v["descuento_extra_pct"]
        subtotal = v.get("subtotal", 0)
        linea(_linea("Subtotal", money(subtotal)))
        linea(_linea("Descuento %g%%" % pct, "-" + money(subtotal * pct / 100)))

    ahorro = v.get("ahorro_total") or 0
    if ahorro > 0.005:
        linea(_linea("Ahorraste", money(ahorro)))

    partes.append(ESC_DOBLE_ON)
    linea(_linea("TOTAL", money(v.get("total", 0)), ancho=ANCHO_TICKET // 2))
    partes.append(ESC_DOBLE_OFF)
    linea(raya)

    metodo = v.get("metodo_pago", "efectivo")
    if metodo == "credito":
        linea(_linea("Pago", "A CREDITO"))
        if v.get("cliente_nombre"):
            linea(_linea("Cliente", v["cliente_nombre"]))
    elif metodo == "tarjeta":
        linea(_linea("Pago", "TARJETA"))
        if v.get("tpv_terminal"):
            linea(_linea("Terminal", v["tpv_terminal"]))
        if v.get("tpv_referencia"):
            linea(_linea("Referencia", v["tpv_referencia"]))
        if v.get("tpv_autorizacion"):
            linea(_linea("Autorizacion", v["tpv_autorizacion"]))
    elif metodo == "transferencia":
        linea(_linea("Pago", "TRANSFERENCIA"))
        if v.get("transferencia_referencia"):
            linea(_linea("Referencia", v["transferencia_referencia"]))
    else:
        linea(_linea("Pago", "EFECTIVO"))
        if v.get("pago_con") is not None:
            linea(_linea("Pago con", money(v["pago_con"])))
            linea(_linea("Cambio", money(v.get("cambio") or 0)))

    partes.append(ESC_CENTRAR)
    linea("Gracias por su compra!")
    partes.append(CORTE_PAPEL)
    return b"".join(partes)


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


def imprimir_ticket(datos_venta):
    _mandar_a_impresora("Ticket de venta", construir_ticket_escpos(datos_venta))


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
                datos_venta = json.loads(self.rfile.read(largo) or b"{}")
                imprimir_ticket(datos_venta)
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
