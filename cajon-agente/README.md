# Agente del punto de venta (cajón de dinero + impresión directa)

Programa chico que se queda corriendo en la PC de Windows donde está conectada
la impresora Xprinter XP-58IIH por USB (la que tiene el cajón EC-CD-50M colgado
del cable RJ11 de atrás). Hace dos cosas, cada vez que se confirma una venta
desde `pagos.html` **en esa misma PC**:

- Si el pago fue en efectivo, le manda a la impresora el byte que dispara el
  pulso de abrir el cajón.
- Imprime el ticket directo a la impresora, sin abrir el diálogo de impresión
  de Windows —el cajero no tiene que tocar nada, sale solo.

Ninguna de las dos cosas las puede hacer el diálogo normal de imprimir
(`window.print()` del navegador): ese diálogo solo sabe entregarle a la
impresora una hoja ya dibujada, nunca esos comandos de control. Por eso hace
falta hablarle a la impresora por otra vía, y el navegador no puede hacerlo
directo sin cambiarle el driver (lo que rompería la impresión normal); este
agente es el puente.

No toca el driver de la impresora ni cambia cómo imprimía antes: usa la API de
impresión de Windows en modo RAW, y si este agente no está corriendo,
`pagos.html` cae sola de vuelta al diálogo de impresión de siempre.

## Antes de empezar

Necesitas esa PC físicamente (o acceso remoto a ella) y permisos para instalar
software. Se hace una sola vez.

## Paso 1 — Copiar estos archivos a la PC

Descomprime el zip en una carpeta fija de esa PC, por ejemplo `C:\cajon-agente\`,
de modo que los 4 archivos (`agente_cajon.py`, `iniciar_agente.vbs`,
`requirements.txt`, este `README.md`) queden juntos ahí. No los dejes en el
Escritorio ni en Descargas por si alguien los borra sin querer.

## Paso 2 — Comprobar si tiene Python

Abre el Símbolo del sistema (busca "cmd" en el menú de inicio) y escribe:

```
python --version
```

- Si responde algo como `Python 3.x.x`, ya tienes Python: pasa al Paso 3.
- Si dice que no se reconoce el comando, instala Python:
  1. Ve a <https://www.python.org/downloads/> y descarga la versión para Windows.
  2. Al instalar, **marca la casilla "Add python.exe to PATH"** en la primera
     pantalla del instalador — es el paso que más se olvida y sin él nada de
     esto funciona.
  3. Cierra y vuelve a abrir el Símbolo del sistema, y repite `python --version`
     para confirmar.

## Paso 3 — Instalar la dependencia

En el mismo Símbolo del sistema:

```
cd C:\cajon-agente
pip install -r requirements.txt
```

Eso instala `pywin32`, que es lo que permite mandarle datos directos a la
impresora desde Python.

## Paso 4 — Confirmar el nombre de la impresora

Abre **Configuración de Windows → Bluetooth y dispositivos → Impresoras y
escáneres** (o Panel de control → Dispositivos e impresoras) y busca el nombre
exacto con el que aparece la Xprinter — puede ser `XP-58IIH`, o algo como
`Xprinter XP-58IIH (Copy 1)` si Windows le agregó algo.

Abre `agente_cajon.py` con el Bloc de notas y busca esta línea, cerca del
principio:

```python
NOMBRE_IMPRESORA = "XP-58IIH"
```

Si el nombre que viste en Windows es distinto, cámbialo aquí exactamente
igual (respetando mayúsculas y espacios) y guarda el archivo.

## Paso 5 — Probar el agente a mano

En el Símbolo del sistema, dentro de `C:\cajon-agente`:

```
python agente_cajon.py
```

Debe imprimir:

```
Agente del punto de venta escuchando en http://127.0.0.1:8788
Impresora configurada: 'XP-58IIH'
```

Y **debe quedarse ahí, esperando** — eso es normal, significa que está
funcionando. No cierres esta ventana todavía.

Para comprobar que responde, abre un navegador en esa misma PC y visita:

```
http://127.0.0.1:8788/
```

Debe mostrar `{"agente": "punto de venta", "estado": "activo"}`.

## Paso 6 — Probar que de verdad abre el cajón y que imprime

Con el agente todavía corriendo (ventana del Paso 5 abierta), abre **otra**
ventana de terminal. Puede ser el Símbolo del sistema (`cmd`) o PowerShell —
Windows moderno trae ambos, y da igual cuál uses, pero **fíjate cuál es**,
porque los comandos de abajo cambian ligeramente entre uno y otro (se nota en
el símbolo antes del cursor: `C:\...>` es `cmd`, `PS C:\...>` es PowerShell).

**Importante si usas PowerShell:** ahí `curl` no es el programa real, es un
alias de `Invoke-WebRequest` con parámetros distintos (no entiende `-X`, por
ejemplo). Usa siempre `curl.exe` (con el `.exe`) para forzar el programa de
verdad — los comandos de abajo ya lo hacen así, y funcionan igual en `cmd`.

**Cajón:**

```
curl.exe -X POST http://127.0.0.1:8788/abrir-cajon
```

El cajón debería abrirse en ese momento.

**Si no abre pero tampoco da error:** el pulso puede estar configurado al pin
equivocado del RJ11. Abre `agente_cajon.py`, busca la línea:

```python
PULSO_ABRIR_CAJON = b"\x1b\x70\x00\x19\xfa"
```

y cambia el tercer byte de `\x00` a `\x01` (ese byte es el que elige el pin:
`\x00` = pin 2, `\x01` = pin 5). Guarda, detén el agente (Ctrl+C en su
ventana) y repite el Paso 5 y esta prueba.

**Impresión del ticket**, con un ticket de ejemplo. Pasar el JSON directo en
la línea de comandos es frágil —`cmd` y PowerShell tratan las comillas de
forma distinta, y es fácil que algo se rompa al copiar—, así que mejor
ponerlo en un archivo aparte y decirle a `curl.exe` que lo lea de ahí: eso
funciona igual sin importar cuál terminal uses.

1. Abre el Bloc de notas, pega exactamente esto (una sola línea):

   ```
   {"id":1,"encabezado":"Prueba","sucursal":"Prueba","operador":"Prueba","fecha":"2026-01-01T12:00:00Z","detalle":[{"nombre":"Producto de prueba","cantidad":1,"precio_unitario":100,"precio_original":null,"importe":100}],"subtotal":100,"descuento_extra_pct":0,"ahorro_total":0,"total":100,"metodo_pago":"efectivo","pago_con":100,"cambio":0}
   ```

2. Guárdalo como `prueba.json` dentro de `C:\cajon-agente\` —en "Guardar
   como", cambia "Tipo" a "Todos los archivos" para que no quede como
   `prueba.json.txt`.

3. Ejecuta (igual en `cmd` o PowerShell, siempre que sea `curl.exe` con el
   `.exe`):

   ```
   curl.exe -X POST http://127.0.0.1:8788/imprimir-ticket -H "Content-Type: application/json" -d "@prueba.json"
   ```

Debe salir un ticket de prueba con el papel cortándose solo al final. Si los
acentos o la "ñ" salen como símbolos raros, o las columnas no alinean bien,
revisa la sección de más abajo.

**Si da un error de impresora no encontrada** (en cualquiera de las dos
pruebas): el nombre del Paso 4 no coincide exactamente. Vuelve a copiarlo tal
cual aparece en Windows.

## Paso 7 — Dejarlo arrancando solo con Windows

Una vez que el Paso 6 funcionó:

1. Cierra la ventana de prueba (Ctrl+C, o simplemente ciérrala).
2. Haz clic derecho sobre `iniciar_agente.vbs` → **Crear acceso directo**.
   Windows crea un archivo nuevo, algo como `iniciar_agente - acceso directo.vbs`.
3. **Corta ese acceso directo** (no el original) y pégalo en la carpeta de
   inicio de Windows: presiona `Windows + R`, escribe `shell:startup` y
   presiona Enter — se abre esa carpeta. Pega el acceso directo ahí.
4. Reinicia la PC (o cierra sesión y vuelve a entrar) para probar que arranca
   solo. No debe abrirse ninguna ventana visible: el agente corre oculto.
5. Repite las pruebas del Paso 6 para confirmar que sigue respondiendo.

## Paso 8 — Activarlo en pagos.html (el paso que falta si nada de esto pasa solo)

Todo lo de arriba deja el agente listo, pero `pagos.html` **no lo usa
automáticamente**: hay que decírselo, una sola vez, desde el navegador de
**esta PC** en concreto —es una configuración del dispositivo, no de tu
usuario, así que si cambias de computadora hay que repetir este paso ahí—.

1. Abre `/pagos` en el navegador de esta PC, con el usuario de siempre.
2. En la barra de arriba hay un ícono 🖨️. Tócalo.
3. Confirma "¿Activar la impresora y el cajón aquí?".
4. El ícono se pone azul: es la señal de que esta PC ya va a intentar abrir el
   cajón e imprimir directo en cada venta.

Desde ese momento, cada venta en esta PC intenta abrir el cajón (si fue en
efectivo) e imprimir el ticket sola. Si el agente deja de responder algún día
—se cerró, la PC se reinició y todavía no arranca—, cae sola de vuelta al
diálogo de impresión de siempre: nunca te quedas sin ticket.

En cualquier otro dispositivo (los iPhone de las demás sucursales, una
tablet) el ícono 🖨️ existe pero no lo actives: ahí no hay impresora ni cajón
conectados, y sin activarlo la pantalla se comporta exactamente igual que
siempre, con el botón manual de "Imprimir" del ticket.

## Si algo deja de funcionar más adelante

- **El cajón/ticket dejaron de abrir o imprimir solos, pero el botón manual
  "Imprimir" del modal sigue funcionando:** probablemente el agente no está
  corriendo. Revisa con el Paso 6; si no responde, ejecútalo a mano con el
  Paso 5 para ver el error exacto.
- **El ícono 🖨️ de pagos.html aparece en gris (no azul) en esta PC:** significa
  que no está activado en este navegador. Repite el Paso 8.
- **Reinstalaron o reemplazaron la impresora:** repite el Paso 4, el nombre
  puede haber cambiado.
- **El ticket imprime pero con acentos/ñ raros, o las columnas no alinean:**
  abre `agente_cajon.py` y ajusta cerca del principio:
  - `ANCHO_TICKET = 32` — súbelo o bájalo (30-33 es el rango normal) si el
    texto se corta antes de tiempo o le sobra mucho espacio a la derecha.
  - Si los acentos salen mal, prueba cambiando `ESC_CODEPAGE_CP850 =
    b"\x1b\x74\x02"` a otro código de página (consulta el manual de la
    Xprinter, la lista de códigos ESC/POS suele estar ahí).
- **Quieres detenerlo temporalmente:** busca `pythonw.exe` en el Administrador
  de tareas de Windows y termínalo ahí; volverá a arrancar solo en el
  siguiente inicio de sesión mientras el acceso directo del Paso 7 siga en la
  carpeta de inicio.
