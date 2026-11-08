"""Grafo propio del tutor (LangGraph StateGraph) con guardrails de entrada y de salida.

    START -> input_guard -> agent <-> tools
                              |
                              v
                        output_guard --(fuga)--> rewrite --> output_guard
                              |                                  |
                              v                                  v (si persiste)
                             END                           safe_fallback -> END

- input_guard: detecta prompt injection y la neutraliza dentro del propio mensaje del alumno.
- agent/tools: bucle ReAct con tope de pasos de herramienta (el prebuilt no lo tiene).
- output_guard: HTML a Markdown, solo el enlace oficial, y sospecha de solución completa + juez LLM.
- rewrite: una sola reformulación socrática si hay fuga.
- safe_fallback: mensaje fijo si la reformulación sigue filtrando la solución.

El informe de cada petición queda en state["guard"] para medirlo en el artículo.
"""
import json
import re
from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

import guardrails as g

MAX_TOOL_STEPS = 4
MAX_REWRITES = 1


class TutorState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    asignatura: str
    student_query: str
    guard: dict
    attempts: int
    leak: bool


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for item in content:
            if isinstance(item, str):
                partes.append(item)
            elif isinstance(item, dict) and "text" in item:
                partes.append(item["text"])
        return "".join(partes)
    return "" if content is None else str(content)


JUDGE_PROMPT = """Eres un revisor pedagógico de un tutor socrático de programación (C/C++ y Linux).
Decide si la RESPUESTA DEL TUTOR entrega la solución completa del problema del alumno.

leak=true: incluye código corregido o un programa completo listo para copiar, o el comando completo de Linux que resuelve lo pedido.
leak=false: explica un concepto, da una pista, señala dónde está el fallo sin corregirlo, o muestra un ejemplo genérico corto que no resuelve el ejercicio del alumno.

CONSULTA DEL ALUMNO:
{consulta}

RESPUESTA DEL TUTOR:
{respuesta}

Responde SOLO con JSON: {{"leak": true|false, "reason": "máximo 15 palabras"}}"""

REWRITE_PROMPT = """Eres un tutor socrático de {materia} de la Universidad de Granada. Tu borrador entrega demasiada solución.
Reescríbelo siguiendo estas reglas:
- No incluyas código corregido, programas completos ni el comando completo que resuelve el problema.
- Señala qué parte debe revisar el alumno y por qué, con una pista o una analogía.
- Puedes citar una línea del código del alumno, pero sin corregirla.
- Mantén el enlace Markdown de los apuntes si el borrador lo tenía, como primera línea.
- Responde solo en Markdown, sin HTML, y termina con una pregunta que guíe su siguiente paso.

CONSULTA DEL ALUMNO:
{consulta}

BORRADOR A REESCRIBIR:
{borrador}"""


async def _judge(judge_llm, consulta: str, respuesta: str) -> Optional[bool]:
    """True = fuga, False = respuesta válida, None = no se pudo decidir."""
    if judge_llm is None:
        return None
    try:
        res = await judge_llm.ainvoke(JUDGE_PROMPT.format(consulta=consulta[:1500], respuesta=respuesta[:6000]))
        m = re.search(r"\{.*\}", _text(res.content), re.DOTALL)
        if not m:
            return None
        return bool(json.loads(m.group(0)).get("leak"))
    except Exception:
        return None


def build_tutor_graph(llm, tools: list, judge_llm=None, rewrite_llm=None):
    """Compila el grafo. `llm` debe soportar bind_tools; judge_llm y rewrite_llm son opcionales."""
    llm_con_tools = llm.bind_tools(tools) if tools else llm
    reescritor = rewrite_llm or llm

    async def input_guard(state: TutorState) -> dict:
        guard = dict(state.get("guard") or {})
        humanos = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        flagged = bool(humanos) and g.detect_injection(_text(humanos[-1].content))
        guard["injection"] = flagged
        salida: dict = {"guard": guard}
        if flagged:
            ultimo = humanos[-1]
            salida["messages"] = [
                HumanMessage(content=f"{_text(ultimo.content)}\n\n[{g.INJECTION_REMINDER}]", id=ultimo.id)
            ]
        return salida

    async def agent(state: TutorState) -> dict:
        mensajes: List[BaseMessage] = state["messages"]
        ultimo_humano = max((i for i, m in enumerate(mensajes) if isinstance(m, HumanMessage)), default=-1)
        pasos = sum(isinstance(m, ToolMessage) for m in mensajes[ultimo_humano + 1:])
        modelo = llm_con_tools if pasos < MAX_TOOL_STEPS else llm
        return {"messages": [await modelo.ainvoke(mensajes)]}

    async def output_guard(state: TutorState) -> dict:
        ultimo = state["messages"][-1]
        asignatura = state.get("asignatura", "cpp")
        limpio, rep = g.sanitize_response(_text(ultimo.content))

        guard = dict(state.get("guard") or {})
        guard.update(
            html_fixed=rep.html_fixed,
            links_removed=rep.links_removed,
            closing_question=g.ends_with_question(limpio),
        )

        # Cita obligatoria: si el tutor consultó los apuntes y no puso el enlace, se añade el de la herramienta
        if not g.has_official_link(limpio):
            ultimo_humano = max((i for i, m in enumerate(state["messages"]) if isinstance(m, HumanMessage)), default=-1)
            for m in state["messages"][ultimo_humano + 1:]:
                if isinstance(m, ToolMessage) and m.name == "buscar_apuntes_ugr":
                    cita = g.citation_from_tool(_text(m.content))
                    if cita:
                        limpio = f"{cita}\n\n{limpio}"
                        guard["citation_added"] = True
                        break

        leak = False
        sospecha = g.suspect_full_solution(limpio, asignatura)
        if sospecha.suspicious:
            guard["suspicious"] = sospecha.reason
            veredicto = await _judge(judge_llm, state.get("student_query", ""), limpio)
            guard["judge"] = {True: "leak", False: "ok", None: "sin_juez"}[veredicto]
            leak = veredicto is not False  # sin veredicto: se asume fuga
        return {"guard": guard, "leak": leak, "messages": [AIMessage(content=limpio, id=ultimo.id)]}

    async def rewrite(state: TutorState) -> dict:
        ultimo = state["messages"][-1]
        materia = "Sistemas Unix/Linux" if state.get("asignatura") == "linux" else "Metodología de la Programación (C/C++)"
        prompt = REWRITE_PROMPT.format(
            materia=materia, consulta=state.get("student_query", "")[:1500], borrador=_text(ultimo.content)
        )
        try:
            nuevo = _text((await reescritor.ainvoke(prompt)).content)
        except Exception:
            nuevo = ""
        guard = dict(state.get("guard") or {})
        guard["rewritten"] = True
        return {
            "attempts": state.get("attempts", 0) + 1,
            "guard": guard,
            "messages": [AIMessage(content=nuevo or _text(ultimo.content), id=ultimo.id)],
        }

    async def safe_fallback(state: TutorState) -> dict:
        ultimo = state["messages"][-1]
        guard = dict(state.get("guard") or {})
        guard["fallback"] = True
        return {
            "guard": guard,
            "leak": False,
            "messages": [AIMessage(content=g.safe_fallback_message(state.get("asignatura", "cpp")), id=ultimo.id)],
        }

    def despues_de_guard(state: TutorState) -> str:
        if not state.get("leak"):
            return END
        return "rewrite" if state.get("attempts", 0) < MAX_REWRITES else "safe_fallback"

    grafo = StateGraph(TutorState)
    grafo.add_node("input_guard", input_guard)
    grafo.add_node("agent", agent)
    grafo.add_node("output_guard", output_guard)
    grafo.add_node("rewrite", rewrite)
    grafo.add_node("safe_fallback", safe_fallback)

    grafo.add_edge(START, "input_guard")
    grafo.add_edge("input_guard", "agent")
    if tools:
        grafo.add_node("tools", ToolNode(tools))
        grafo.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "output_guard"})
        grafo.add_edge("tools", "agent")
    else:
        grafo.add_edge("agent", "output_guard")
    grafo.add_conditional_edges("output_guard", despues_de_guard, {"rewrite": "rewrite", "safe_fallback": "safe_fallback", END: END})
    grafo.add_edge("rewrite", "output_guard")
    grafo.add_edge("safe_fallback", END)
    return grafo.compile()
