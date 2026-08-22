' Arranca el agente del cajón sin abrir ninguna ventana de consola.
' No mover ni copiar este archivo suelto: si lo mueves, mueve toda la carpeta
' junto con él (usa la ruta de sí mismo para encontrar agente_cajon.py al lado).
'
' Para que arranque solo con Windows: NO pongas este archivo directo en la
' carpeta de inicio. Crea un ACCESO DIRECTO a este archivo (clic derecho >
' Crear acceso directo) y mueve ese acceso directo a la carpeta de inicio
' (Windows+R, escribe  shell:startup , Enter). Los pasos completos están en
' README.md.

Set fso = CreateObject("Scripting.FileSystemObject")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
' 0 = ventana oculta · False = no esperar a que termine (queda corriendo)
objShell.Run "pythonw.exe """ & carpeta & "\agente_cajon.py""", 0, False
