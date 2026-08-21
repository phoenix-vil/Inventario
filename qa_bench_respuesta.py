#!/usr/bin/env python3
"""
Segunda fase del banco de pruebas: calidad de la respuesta final.

El modelo ya eligió la herramienta; ahora recibe el resultado del endpoint
(datos reales de la base de QA) y tiene que redactar la respuesta al usuario.
Lo que se vigila:
  - que responda en español
  - que no invente ni recalcule cifras (las cifras deben venir del endpoint)
  - que no filtre razonamiento interno al texto visible

Uso:  python3 qa_bench_respuesta.py llama3.2:3b qwen3:4b
"""

import json
import re
import sys
import unicodedata

from qa_bench_chatbot import HERRAMIENTAS, SISTEMA, OLLAMA  # noqa: F401
import urllib.request
import time

# (pregunta, llamada que hizo el modelo, resultado del endpoint, cifras que
#  deben aparecer, cifras que NO deben aparecer porque implican inventar/calcular)
CASOS = [
    (
        "¿A cuánto vendo el Waste away 240ml?",
        {"name": "buscar_producto", "arguments": {"nombre": "Waste away"}},
        {"nombre": "Waste away 240ml", "precio_venta": 450.0, "stock": 1, "marca": "Dr. Tims"},
        ["450"],
        [],
    ),
    (
        "¿cómo vamos de ventas hoy?",
        {"name": "resumen_ventas", "arguments": {"periodo": "hoy"}},
        {"periodo": "hoy", "total_vendido": 4820.5, "tickets": 7, "ticket_promedio": 688.64},
        ["4820.5", "7"],
        [],
    ),
    (
        "¿Cuántos calentadores Sunny quedan en Reptile?",
        {"name": "stock_por_sucursal", "arguments": {"producto": "Calentador Sunny", "sucursal": "Reptile"}},
        {
            "producto": "Calentador Sunny 200w SGH-280",
            "por_sucursal": [
                {"sucursal": "Reptile", "cantidad": 3},
                {"sucursal": "Plaza", "cantidad": 1},
            ],
        },
        ["3"],
        [],
    ),
    (
        "¿quién me debe dinero?",
        {"name": "deuda_clientes", "arguments": {}},
        {
            "deudores": [
                {"cliente": "Melanie Mendez", "deuda": 1250.0, "limite_credito": 2000.0},
                {"cliente": "Juan perez", "deuda": 380.5, "limite_credito": None},
            ],
            "total_por_cobrar": 1630.5,
        },
        ["1250", "380.5"],
        [],
    ),
    (
        "¿tenemos Coconut Chips?",
        {"name": "buscar_producto", "arguments": {"nombre": "Coconut Chips"}},
        {"nombre": "Coconut Chips 500g", "precio_venta": 150.0, "stock": 0, "marca": "ZooMed"},
        # con stock 0 tiene que negar, no afirmar que hay existencia
        ["no ten|no hay|sin exist|agotad"],
        [],
    ),
]

PALABRAS_EN = re.compile(
    r"\b(the|user|is asking|let me|okay|i should|i need to|tool|according to|based on)\b", re.I
)


def normaliza(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def responde(modelo, pregunta_txt, llamada, resultado):
    mensajes = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": pregunta_txt},
        {"role": "assistant", "content": "", "tool_calls": [{"function": llamada}]},
        {"role": "tool", "content": json.dumps(resultado, ensure_ascii=False),
         "tool_name": llamada["name"]},
    ]
    cuerpo = {"model": modelo, "messages": mensajes, "tools": HERRAMIENTAS,
              "stream": False, "options": {"temperature": 0}}
    req = urllib.request.Request(OLLAMA, data=json.dumps(cuerpo).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.loads(r.read())
    return resp["message"].get("content", ""), time.time() - t0


def evalua(modelo):
    print(f"\n{'='*74}\n  {modelo} — calidad de respuesta\n{'='*74}")
    buenas = 0
    for pregunta_txt, llamada, resultado, deben, no_deben in CASOS:
        try:
            texto, seg = responde(modelo, pregunta_txt, llamada, resultado)
        except Exception as e:
            print(f"  ERROR {pregunta_txt[:40]}: {e}")
            continue

        ingles = bool(PALABRAS_EN.search(texto))

        # Valores numéricos que trae el resultado del endpoint
        def valores(obj):
            if isinstance(obj, bool) or obj is None:
                return set()
            if isinstance(obj, (int, float)):
                return {round(float(obj), 2)}
            if isinstance(obj, str):
                return {round(float(n.replace(",", "")), 2)
                        for n in re.findall(r"\d[\d,]*(?:\.\d+)?", obj)}
            if isinstance(obj, dict):
                return set().union(*(valores(v) for v in obj.values())) if obj else set()
            if isinstance(obj, list):
                return set().union(*(valores(v) for v in obj)) if obj else set()
            return set()

        del_endpoint = valores(resultado)
        # Números escritos en el texto, respetando el punto decimal ($4,820.50 -> 4820.5)
        escritos = {round(float(n.replace(",", "")), 2)
                    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", texto)}

        def presente(v):
            """¿El valor v viene del endpoint? (para detectar cifras inventadas)"""
            return any(abs(v - d) < 0.01 for d in del_endpoint)

        def en_texto(v):
            """¿El modelo escribió el valor v en su respuesta?"""
            return any(abs(v - e) < 0.01 for e in escritos)

        # `deben` acepta cifras ("450") o frases que deben aparecer ("no hay")
        limpio = normaliza(texto)

        def cumple(c):
            try:
                return en_texto(round(float(c), 2))
            except ValueError:
                return any(v in limpio for v in normaliza(c).split("|"))

        faltan = [c for c in deben if not cumple(c)]
        # Solo cuentan como inventadas las cifras "de negocio" (>=100), para no
        # marcar cantidades pequeñas o números sueltos de la redacción.
        inventados = sorted(v for v in escritos if v >= 100 and not presente(v))

        ok = not faltan and not ingles and not inventados

        if ok:
            buenas += 1
        problemas = []
        if faltan:
            problemas.append(f"faltan cifras {faltan}")
        if ingles:
            problemas.append("razonamiento/inglés visible")
        if inventados:
            problemas.append(f"cifras inventadas {sorted(inventados)}")

        print(f"\n  {'OK  ' if ok else 'FALLA'} {pregunta_txt}  ({seg:.1f}s)")
        print(f"    → {texto.strip()[:300]}")
        if problemas:
            print(f"    ⚠ {'; '.join(problemas)}")

    print(f"\n  Respuestas limpias: {buenas}/{len(CASOS)}")
    return buenas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for m in sys.argv[1:]:
        evalua(m)
