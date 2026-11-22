"""Acceso directo al agente del tutor para las medidas (sin pasar por HTTP).

Se invoca solo el agente primario (Gemini). Si falla no se cae a Groq: una medida hecha con otro modelo
sin avisar no vale. Los textos completos se guardan fuera del repositorio (`docs/bench/tutor/`), porque
pueden citar fragmentos de los apuntes; en `resultados/` solo van las métricas.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
import tutor  # noqa: E402
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
PRIVADO = os.path.join(os.path.dirname(c.BENCH_DIR), "docs", "bench", "tutor")
with open(os.path.join(AQUI, "proyectos.json"), encoding="utf-8") as f:
    PROYECTOS = json.load(f)

MODELOS = {"gemini": tutor.GEMINI_MODEL, "groq": tutor.GROQ_MODEL, "modo": "grafo" if tutor._graph_enabled() else "prefabricado"}


class CuotaAgotada(Exception):
    pass


def es_cuota(e: Exception) -> bool:
    t = str(e).lower()
    return "429" in t or "quota" in t or "resource_exhausted" in t or "rate limit" in t


async def preguntar(consulta: str, asignatura: str, proyecto: str) -> dict:
    """Devuelve texto, herramientas llamadas (en orden), informe del guardrail, ruta y latencia."""
    archivos = PROYECTOS[proyecto]
    if tutor._es_saludo_o_charla(consulta):
        t0 = time.perf_counter()
        texto = await tutor.get_socratic_response_async([{"role": "user", "content": consulta}], archivos, "", asignatura)
        return {"texto": texto, "herramientas": [], "guard": {}, "ruta": "rapida", "ms": (time.perf_counter() - t0) * 1000}
    mensajes = tutor._build_context_and_messages([{"role": "user", "content": consulta}], archivos, "", asignatura)
    primario, _ = await tutor._get_agents()
    if not tutor._runtime.mcp_ok:
        raise RuntimeError("El servidor MCP no arrancó: sin herramientas no hay medida")
    token = tutor._current_project_context.set(archivos)
    t0 = time.perf_counter()
    try:
        res = await primario.ainvoke(tutor._agent_input(mensajes, asignatura, consulta))
    except Exception as e:
        if es_cuota(e):
            raise CuotaAgotada(str(e)[:200]) from e
        raise
    finally:
        tutor._current_project_context.reset(token)
    ms = (time.perf_counter() - t0) * 1000
    herramientas = [tc["name"] for m in res["messages"] if isinstance(m, AIMessage) for tc in (m.tool_calls or [])]
    salidas = [{"herramienta": m.name, "texto": tutor._extract_text_content(m.content)[:1500]}
               for m in res["messages"] if isinstance(m, ToolMessage)]
    return {"texto": tutor._extract_text_content(res["messages"][-1].content), "herramientas": herramientas,
            "guard": res.get("guard") or {}, "ruta": "agente", "ms": ms, "salidas_herramientas": salidas}


def guardar_privado(nombre: str, registro: dict) -> None:
    os.makedirs(PRIVADO, exist_ok=True)
    with open(os.path.join(PRIVADO, nombre + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def leer_privado(nombre: str) -> list:
    ruta = os.path.join(PRIVADO, nombre + ".jsonl")
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
