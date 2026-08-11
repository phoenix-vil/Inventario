#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[QA] Corrige el calculo de altura del PDF: ahora contempla que los
nombres largos de producto pueden ocupar 2+ lineas, para que la pagina
sea lo bastante alta y no se pierda el pie de pagina.
Uso: cd ~/inventario-qa/static && python3 qa_fix_altura_footer.py
"""
import os, re

STATIC = os.path.expanduser('~/inventario-qa/static')

viejo = '''async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;
  const numItems = (v.detalle||[]).length;
  let alturaEstimada = 260 + numItems * 15;
  if(v.descuento_extra_pct>0) alturaEstimada += 36;
  const ahorroTk0 = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk0>0.005) alturaEstimada += 18;
  alturaEstimada = Math.max(alturaEstimada, 340);

  const doc = new jsPDFCtor({ unit:'pt', format:[320, alturaEstimada], orientation:'portrait' });'''

nuevo = '''async function generarPDFTicketVenta(v){
  const jsPDFCtor = window.jspdf.jsPDF;

  // Medir cuantas lineas ocupara REALMENTE cada producto (los nombres
  // largos se envuelven a 2+ lineas) antes de decidir el alto de la pagina
  const docMedidor = new jsPDFCtor({ unit:'pt', format:[320, 1000] });
  docMedidor.setFont('courier','bold'); docMedidor.setFontSize(9);
  let lineasTotalItems = 0;
  (v.detalle||[]).forEach(function(it){
    const cant = Number.isInteger(it.cantidad)?it.cantidad+'x':it.cantidad.toFixed(3)+'kg';
    const lineas = docMedidor.splitTextToSize(cant+' '+it.nombre, 190);
    lineasTotalItems += lineas.length;
  });

  let alturaEstimada = 260 + lineasTotalItems * 15;
  if(v.descuento_extra_pct>0) alturaEstimada += 36;
  const ahorroTk0 = v.ahorro_total!=null?v.ahorro_total:0;
  if(ahorroTk0>0.005) alturaEstimada += 18;
  alturaEstimada = Math.max(alturaEstimada, 340) + 20;

  const doc = new jsPDFCtor({ unit:'pt', format:[320, alturaEstimada], orientation:'portrait' });'''

total = 0
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    src = open(ruta, encoding='utf-8').read()
    n = src.count(viejo)
    if n == 1:
        src = src.replace(viejo, nuevo, 1)
        open(ruta, 'w', encoding='utf-8').write(src)
        print("OK " + nombre + ": altura del PDF ahora contempla nombres largos")
        total += 1
    elif 'docMedidor' in src:
        print("* " + nombre + ": ya estaba corregido")
    else:
        print("ERROR " + nombre + ": no se encontro el bloque exacto (coincidencias: " + str(n) + ")")

print()
ok_total = True
for nombre in ['pagos.html', 'historial.html']:
    ruta = os.path.join(STATIC, nombre)
    s = open(ruta, encoding='utf-8').read()
    scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', s, re.DOTALL)
    ok = all(x.count('{') == x.count('}') for x in scripts)
    print("Balance de llaves en " + nombre + ":", "OK" if ok else "DESBALANCEADO")
    if not ok:
        ok_total = False

print()
print("=" * 55)
if ok_total:
    print("Reiniciando inventario-qa (NO produccion)...")
    os.system("sudo systemctl restart inventario-qa")
    print("Listo. El pie de pagina ya no deberia desaparecer, sin importar")
    print("que tan largos sean los nombres de los productos.")
else:
    print("ADVERTENCIA: desbalance de llaves. NO se reinicio el servicio.")
