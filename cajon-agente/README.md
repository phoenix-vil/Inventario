# Agente del cajón de dinero

Programa chico que se queda corriendo en la PC de Windows donde está conectada
la impresora Xprinter XP-58IIH por USB (la que tiene el cajón EC-CD-50M colgado
del cable RJ11 de atrás). Su único trabajo es escuchar cuando `pagos.html`
confirma un cobro en efectivo y, en ese momento, mandarle a la impresora el
byte que dispara el pulso de abrir el cajón — algo que el diálogo normal de
imprimir de Windows nunca hace.

No toca el driver de la impresora ni cambia cómo se imprimen los tickets hoy:
solo agrega la apertura del cajón al lado.

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
Agente del cajón escuchando en http://127.0.0.1:8788
Impresora configurada: 'XP-58IIH'
```

Y **debe quedarse ahí, esperando** — eso es normal, significa que está
funcionando. No cierres esta ventana todavía.

Para comprobar que responde, abre un navegador en esa misma PC y visita:

```
http://127.0.0.1:8788/
```

Debe mostrar `{"agente": "cajon de dinero", "estado": "activo"}`.

## Paso 6 — Probar que de verdad abre el cajón

Con el agente todavía corriendo (ventana del Paso 5 abierta), abre **otro**
Símbolo del sistema y ejecuta:

```
curl -X POST http://127.0.0.1:8788/abrir-cajon
```

El cajón debería abrirse en ese momento. Si no tienes `curl`, entra desde el
navegador a `http://127.0.0.1:8788/abrir-cajon` — no es la forma correcta
(esa ruta espera un POST, no un GET) pero muchos navegadores lo intentan igual
y sirve para una prueba rápida; si no abre así, usa el `curl` de arriba.

**Si no abre pero tampoco da error:** el pulso puede estar configurado al pin
equivocado del RJ11. Abre `agente_cajon.py`, busca la línea:

```python
PULSO_ABRIR_CAJON = b"\x1b\x70\x00\x19\xfa"
```

y cambia el tercer byte de `\x00` a `\x01` (ese byte es el que elige el pin:
`\x00` = pin 2, `\x01` = pin 5). Guarda, detén el agente (Ctrl+C en su
ventana) y repite el Paso 5 y el Paso 6.

**Si da un error de impresora no encontrada:** el nombre del Paso 4 no
coincide exactamente. Vuelve a copiarlo tal cual aparece en Windows.

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
5. Repite la prueba del Paso 6 para confirmar que sigue respondiendo.

Listo. De ahora en adelante, cada vez que se cobre en efectivo desde esta PC,
`pagos.html` va a pedirle a este agente que abra el cajón automáticamente.
Desde cualquier otro dispositivo (los iPhone de las demás sucursales, una
tablet) esa petición simplemente no encuentra a nadie escuchando y no pasa
nada — no da error ni interrumpe el cobro, es el comportamiento esperado.

## Si algo deja de funcionar más adelante

- **El cajón dejó de abrir pero los tickets se siguen imprimiendo bien:**
  probablemente el agente no está corriendo. Revisa con el Paso 6; si no
  responde, ejecútalo a mano con el Paso 5 para ver el error exacto.
- **Reinstalaron o reemplazaron la impresora:** repite el Paso 4, el nombre
  puede haber cambiado.
- **Quieres detenerlo temporalmente:** busca `pythonw.exe` en el Administrador
  de tareas de Windows y termínalo ahí; volverá a arrancar solo en el
  siguiente inicio de sesión mientras el acceso directo del Paso 7 siga en la
  carpeta de inicio.
