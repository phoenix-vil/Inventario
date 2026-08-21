#!/usr/bin/env python3
"""
Banco de pruebas: ¿sirve un modelo local para el chatbot del inventario?

Mide dos cosas sobre modelos servidos por Ollama:
  1. Acierto de tool-calling: dada una pregunta en español, ¿elige la
     herramienta correcta y con los argumentos correctos?
  2. Velocidad: tokens por segundo y latencia total por respuesta.

Las herramientas imitan endpoints reales de main.py. El modelo NUNCA
calcula nada: solo decide a qué endpoint llamar.

Uso:
    python3 qa_bench_chatbot.py qwen3:4b llama3.2:3b
    python3 qa_bench_chatbot.py --think qwen3:4b      # con razonamiento
"""

import json
import sys
import time
import unicodedata
import urllib.request

OLLAMA = "http://localhost:11434/api/chat"
TIMEOUT = 300

# ─── Herramientas (espejo de los endpoints reales de main.py) ──────────────

HERRAMIENTAS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_producto",
            "description": (
                "Busca un producto del inventario por nombre o marca y devuelve "
                "su precio de venta y existencias totales. Úsala cuando pregunten "
                "cuánto cuesta algo, a cuánto se vende, o si hay existencia."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre o parte del nombre del producto, p. ej. 'Waste away' o 'calentador'",
                    }
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stock_por_sucursal",
            "description": (
                "Devuelve cuántas piezas de un producto hay en cada sucursal. "
                "Úsala cuando la pregunta mencione una sucursal concreta o pregunte "
                "dónde hay existencia. Sucursales: Imprenta, Jardincito, Plaza, "
                "Reptile, Only Enterprises."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto": {"type": "string", "description": "Nombre del producto"},
                    "sucursal": {
                        "type": "string",
                        "description": "Nombre de la sucursal. Omitir para ver todas.",
                    },
                },
                "required": ["producto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_ventas",
            "description": (
                "Resumen de ventas del negocio: total vendido, número de tickets y "
                "ganancia. Úsala para preguntas sobre cómo van las ventas, cuánto se "
                "vendió o comparaciones entre periodos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo": {
                        "type": "string",
                        "enum": ["hoy", "ayer", "semana", "mes"],
                        "description": "Periodo a consultar",
                    }
                },
                "required": ["periodo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "productos_stock_bajo",
            "description": (
                "Lista los productos cuyas existencias están en o por debajo del "
                "stock mínimo. Úsala para preguntas sobre qué se está agotando o "
                "qué hay que resurtir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Filtrar por categoría o marca, p. ej. 'Seachem'. Opcional.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deuda_clientes",
            "description": (
                "Consulta cuánto deben los clientes a crédito y su límite de crédito. "
                "Úsala para preguntas sobre deudas, cobranza o crédito de clientes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente": {
                        "type": "string",
                        "description": "Nombre del cliente. Omitir para ver a todos los deudores.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_gastos",
            "description": (
                "Resumen de los gastos ya registrados del negocio, agrupados por "
                "categoría. Úsala para preguntas sobre en qué se ha gastado dinero. "
                "NO sirve para registrar un gasto nuevo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo": {
                        "type": "string",
                        "enum": ["hoy", "semana", "mes"],
                        "description": "Periodo a consultar",
                    }
                },
                "required": ["periodo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_gasto",
            "description": (
                "Registra un GASTO NUEVO en el sistema. Es una acción que modifica "
                "datos: úsala solo cuando el usuario pida explícitamente registrar, "
                "anotar o dar de alta un gasto con su monto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "concepto": {"type": "string", "description": "Descripción del gasto"},
                    "monto": {"type": "number", "description": "Monto en pesos"},
                },
                "required": ["concepto", "monto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_productos",
            "description": (
                "Devuelve los productos más vendidos en un periodo, ordenados por "
                "unidades o por dinero vendido."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo": {
                        "type": "string",
                        "enum": ["hoy", "semana", "mes"],
                        "description": "Periodo a consultar",
                    },
                    "limite": {"type": "integer", "description": "Cuántos productos devolver"},
                },
                "required": ["periodo"],
            },
        },
    },
]

SISTEMA = (
    "Eres el asistente del sistema de inventario y punto de venta de una tienda "
    "de acuarismo y reptiles. Respondes en español, de forma breve y directa.\n\n"
    "Nunca calcules cifras tú mismo ni las inventes: para cualquier dato de "
    "precios, existencias, ventas, gastos o deudas usa la herramienta "
    "correspondiente. Si la pregunta no requiere datos del sistema, responde "
    "directamente sin usar herramientas."
)

# ─── Casos de prueba (preguntas reales, datos reales de la base de QA) ─────
# esperado = None  →  el acierto es NO llamar ninguna herramienta

CASOS = [
    # Consultas directas de producto
    ("¿A cuánto vendo el Waste away 240ml?", "buscar_producto", "nombre", "waste away"),
    ("cuanto cuesta el foco hidroponico", "buscar_producto", "nombre", "foco"),
    ("¿tenemos Coconut Chips?", "buscar_producto", "nombre", "coconut"),
    # Stock por sucursal
    ("¿Cuántos calentadores Sunny quedan en Reptile?", "stock_por_sucursal", "sucursal", "reptile"),
    ("dónde hay Phosphat-E, en qué sucursal", "stock_por_sucursal", "producto", "phosphat"),
    ("checa el stock de Repashy en Jardincito", "stock_por_sucursal", "sucursal", "jardincito"),
    # Ventas
    ("¿cómo vamos de ventas hoy?", "resumen_ventas", "periodo", "hoy"),
    ("cuánto vendimos esta semana", "resumen_ventas", "periodo", "semana"),
    ("dame el total del mes", "resumen_ventas", "periodo", "mes"),
    # Stock bajo
    ("¿qué se está acabando?", "productos_stock_bajo", None, None),
    ("qué productos de Seachem tengo que resurtir", "productos_stock_bajo", "categoria", "seachem"),
    # Clientes / crédito
    ("¿quién me debe dinero?", "deuda_clientes", None, None),
    ("cuánto debe Melanie Mendez", "deuda_clientes", "cliente", "melanie"),
    # Gastos: consultar vs registrar (la trampa)
    ("¿en qué he gastado más este mes?", "resumen_gastos", "periodo", "mes"),
    ("anota un gasto de 350 pesos de gasolina", "registrar_gasto", "concepto", "gasolina"),
    ("cuánto llevo gastado esta semana", "resumen_gastos", "periodo", "semana"),
    # Top productos
    ("cuáles son los 5 productos que más se venden este mes", "top_productos", "periodo", "mes"),
    # Sin herramienta
    ("hola, ¿qué puedes hacer?", None, None, None),
    ("gracias, eso era todo", None, None, None),
]


def normaliza(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def pregunta(modelo, texto, think=None):
    cuerpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": texto},
        ],
        "tools": HERRAMIENTAS,
        "stream": False,
        "options": {"temperature": 0},
    }
    if think is not None:
        cuerpo["think"] = think

    datos = json.dumps(cuerpo).encode()
    req = urllib.request.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        resp = json.loads(r.read())
    return resp, time.time() - t0


def evalua(modelo, think=None):
    etiqueta = modelo + (" (think)" if think else "")
    print(f"\n{'='*74}\n  {etiqueta}\n{'='*74}")

    aciertos = 0
    tok_s = []
    latencias = []
    fallos = []

    for texto, esp_tool, esp_arg, esp_val in CASOS:
        try:
            resp, seg = pregunta(modelo, texto, think)
        except Exception as e:
            print(f"  ERROR  {texto[:45]:<47} {e}")
            fallos.append((texto, f"error: {e}"))
            continue

        msg = resp.get("message", {})
        llamadas = msg.get("tool_calls") or []
        obtenido = llamadas[0]["function"]["name"] if llamadas else None
        args = llamadas[0]["function"].get("arguments", {}) if llamadas else {}

        ok = obtenido == esp_tool
        detalle = ""
        if ok and esp_arg:
            valor = normaliza(args.get(esp_arg, ""))
            if normaliza(esp_val) not in valor:
                ok = False
                detalle = f"arg {esp_arg}={args.get(esp_arg)!r} (esperaba ~{esp_val!r})"
        if ok:
            aciertos += 1
        else:
            if not detalle:
                detalle = f"eligió {obtenido or 'ninguna'} (esperaba {esp_tool or 'ninguna'})"
            fallos.append((texto, detalle))

        ev, evd = resp.get("eval_count", 0), resp.get("eval_duration", 0)
        if ev and evd:
            tok_s.append(ev / (evd / 1e9))
        latencias.append(seg)

        print(f"  {'OK  ' if ok else 'FALLA'} {texto[:45]:<47} {seg:5.1f}s  {detalle}")

    n = len(CASOS)
    print(f"\n  Acierto: {aciertos}/{n} ({100*aciertos/n:.0f}%)")
    if tok_s:
        print(f"  Generación: {sum(tok_s)/len(tok_s):.1f} tok/s")
    print(f"  Latencia: mediana {sorted(latencias)[len(latencias)//2]:.1f}s, "
          f"máx {max(latencias):.1f}s")
    return {
        "modelo": etiqueta,
        "aciertos": aciertos,
        "total": n,
        "tok_s": sum(tok_s) / len(tok_s) if tok_s else 0,
        "lat_mediana": sorted(latencias)[len(latencias) // 2] if latencias else 0,
        "fallos": fallos,
    }


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    think = True if "--think" in sys.argv else (False if "--no-think" in sys.argv else None)
    if not args:
        print(__doc__)
        sys.exit(1)

    resultados = [evalua(m, think) for m in args]

    print(f"\n{'='*74}\n  RESUMEN\n{'='*74}")
    print(f"  {'modelo':<22} {'acierto':>10} {'tok/s':>8} {'latencia':>10}")
    for r in resultados:
        print(f"  {r['modelo']:<22} {r['aciertos']:>4}/{r['total']:<5} "
              f"{r['tok_s']:>8.1f} {r['lat_mediana']:>9.1f}s")

    for r in resultados:
        if r["fallos"]:
            print(f"\n  Fallos de {r['modelo']}:")
            for texto, det in r["fallos"]:
                print(f"    - {texto}\n      {det}")
