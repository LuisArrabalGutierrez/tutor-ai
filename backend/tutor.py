import os
import json
from contextvars import ContextVar
from typing import AsyncGenerator, Dict, List, Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from services.search import search_theory_logic
from services.compiler import compile_and_run_project

load_dotenv()

# ContextVar para aislamiento seguro de archivos por petición sin tocar disco
_current_project_context: ContextVar[Dict[str, str]] = ContextVar("current_project_context", default={})

# --- HERRAMIENTAS DIRECTAS EN MEMORIA (0ms cold-start, sin subprocesos IPC) ---

@tool
def buscar_apuntes_ugr(pregunta: str) -> str:
    """
    Busca en la base de datos de apuntes oficiales de la UGR mediante pgvector.
    USO OBLIGATORIO: Cuando el alumno pregunta teoría, temario o conceptos de C++ o Linux.
    NO USAR para saludos ni para corregir código sin dudas teóricas.
    """
    return search_theory_logic(pregunta)

@tool
async def compilar_cpp() -> str:
    """
    Compila y ejecuta el proyecto C++ actual del alumno dentro del sandbox seguro de Docker.
    USO: Solo si el alumno pide explícitamente ejecutar su código o pregunta por qué da error de compilación.
    """
    archivos = _current_project_context.get()
    if not archivos:
        return "Error: No hay archivos de código en el proyecto actual."
    try:
        resultado = await compile_and_run_project(archivos)
        return resultado.get("output", "Compilación finalizada sin salida.")
    except Exception as e:
        return f"Error en sandbox de compilación: {str(e)}"

@tool
def buscar_internet(consulta: str) -> str:
    """
    Busca información en internet mediante DuckDuckGo si el concepto no está en los apuntes UGR.
    """
    try:
        from duckduckgo_search import DDGS
        resultados = DDGS().text(consulta, max_results=3)
        if not resultados:
            return "Sin resultados en internet."
        texto = "Resultados web:\n"
        for r in resultados:
            texto += f"- {r.get('title', '')}: {r.get('body', '')}\n"
        return texto
    except Exception as e:
        return f"Búsqueda web no disponible: {str(e)}"

# Herramientas unificadas
tutor_tools = [buscar_apuntes_ugr, compilar_cpp, buscar_internet]

# --- INICIALIZACIÓN DEL LLM Y AGENTE EN MEMORIA (SINGLETON) ---
# Modelo de producción ultrarrápido en Groq con soporte nativo de Tool Calling
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=GROQ_MODEL,
    temperature=0.3
)

# Compilación única del agente en memoria al arrancar el backend
agent_executor = create_react_agent(llm, tools=tutor_tools)


def _build_context_and_messages(
    historial: List[dict],
    proyecto_archivos: Dict[str, str],
    terminal_context: str = "",
    asignatura: str = "cpp",
    perfil_alumno: Optional[dict] = None
) -> List:
    """Construye y poda el contexto para minimizar el prefill de tokens y maximizar la velocidad."""
    
    # 1. Perfil Formativo
    texto_perfil = ""
    if perfil_alumno:
        fortalezas = perfil_alumno.get('fortalezas', 'Pendiente de analizar')
        carencias = perfil_alumno.get('carencias', 'Pendiente de analizar')
        texto_perfil = f"\n=== PERFIL DEL ALUMNO ===\n- Fortalezas: {fortalezas}\n- Debilidades: {carencias}\n"

    # 2. Rol y Reglas Socráticas
    if asignatura == "linux":
        rol_sistema = f"""Eres el Profesor Socrático de 'Sistemas y Órdenes Unix/Linux' de la Universidad de Granada (UGR).{texto_perfil}
REGLAS SOCRÁTICAS ESTRICTAS:
0. SALUDOS: Si el alumno solo saluda, responde amigablemente SIN usar herramientas.
1. TEORÍA: Si pregunta teoría, usa OBLIGATORIAMENTE 'buscar_apuntes_ugr'.
2. CITAS: Tu respuesta DEBE comenzar con el enlace Markdown exacto devuelto por los apuntes: [tema.pdf - Diapositiva X](url).
3. GUÍA SOCRÁTICA: Nunca des el comando completo resuelto. Explica la lógica (permisos, tuberías, procesos) y pide al alumno que deduzca el comando.
4. CIERRE: Concluye siempre con una pregunta que guíe su próximo paso."""
        texto_terminal = f"\n=== TERMINAL LINUX ===\n{terminal_context.strip()}" if terminal_context.strip() else ""
    else:
        rol_sistema = f"""Eres el Tutor Socrático de 'Metodología de la Programación' en C/C++ de la Universidad de Granada (UGR).{texto_perfil}
REGLAS SOCRÁTICAS ESTRICTAS:
0. SALUDOS: Si el alumno solo saluda o hace charla informal, responde breve y afable SIN herramientas.
1. TEORÍA: Si pregunta teoría o conceptos del temario, usa 'buscar_apuntes_ugr'.
2. CITAS OBLIGATORIAS: Si usas apuntes, la primera línea de tu respuesta DEBE ser el enlace Markdown: [tema.pdf - Diapositiva X](url).
3. COMPILADOR: Usa 'compilar_cpp' únicamente cuando el alumno lo solicite o haya un error de compilación.
4. NO DAR LA SOLUCIÓN DIRECTA: Corrige mediante pistas, analogías y preguntas reflexivas sobre el código.
5. CIERRE: Concluye siempre con una pregunta socrática."""
        texto_terminal = ""

    # 3. Ventana de historial (últimos 8 mensajes)
    MAX_HISTORIAL = 8
    historial_recortado = historial[-MAX_HISTORIAL:] if len(historial) > MAX_HISTORIAL else historial
    
    mensajes = [SystemMessage(content=rol_sistema)]
    for msg in historial_recortado[:-1]:
        if msg.get("role") == "user":
            mensajes.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            mensajes.append(AIMessage(content=msg.get("content", "")))

    # 4. Poda inteligente de archivos del proyecto (Prompt Pruning)
    ultima_pregunta = historial[-1].get("content", "") if historial else ""
    es_saludo_breve = len(ultima_pregunta.strip().split()) <= 3 and any(
        s in ultima_pregunta.lower() for s in ["hola", "buenas", "hey", "buenos dias", "buenas tardes"]
    )

    if es_saludo_breve or not proyecto_archivos:
        contexto_archivos = "(Sin archivos o pregunta conversacional)"
    else:
        # Poda: Solo incluimos hasta 8.000 caracteres de archivos de código relevantes (.cpp, .h, .c, Makefile)
        archivos_relevantes = {}
        total_len = 0
        for nombre, contenido in proyecto_archivos.items():
            if nombre.endswith(('.cpp', '.h', '.hpp', '.c', 'Makefile', 'makefile')):
                frag = contenido[:2500]
                archivos_relevantes[nombre] = frag
                total_len += len(frag)
                if total_len > 8000:
                    break
        contexto_archivos = json.dumps(archivos_relevantes, indent=2)

    prompt_usuario = f"""=== ARCHIVOS DEL PROYECTO ===
{contexto_archivos}{texto_terminal}

=== CONSULTA DEL ALUMNO ===
{ultima_pregunta}"""

    mensajes.append(HumanMessage(content=prompt_usuario))
    return mensajes


async def get_socratic_response_async(
    historial: list,
    proyecto_archivos: dict,
    terminal_context: str = "",
    asignatura: str = "cpp",
    perfil_alumno: dict = None
) -> str:
    """Genera la respuesta completa socrática (para endpoints síncronos y tests automatizados)."""
    token_context = _current_project_context.set(proyecto_archivos or {})
    try:
        mensajes = _build_context_and_messages(
            historial=historial,
            proyecto_archivos=proyecto_archivos,
            terminal_context=terminal_context,
            asignatura=asignatura,
            perfil_alumno=perfil_alumno
        )
        respuesta = await agent_executor.ainvoke({"messages": mensajes})
        return respuesta["messages"][-1].content
    except Exception as e:
        print(f"❌ [Tutor] Error en agente: {e}")
        return f"Disculpa, ha ocurrido un error al procesar tu consulta: {str(e)}"
    finally:
        _current_project_context.reset(token_context)


async def get_socratic_response_stream_async(
    historial: list,
    proyecto_archivos: dict,
    terminal_context: str = "",
    asignatura: str = "cpp",
    perfil_alumno: dict = None
) -> AsyncGenerator[str, None]:
    """Transmite en streaming los tokens de la respuesta socrática a medida que Groq los genera."""
    token_context = _current_project_context.set(proyecto_archivos or {})
    try:
        mensajes = _build_context_and_messages(
            historial=historial,
            proyecto_archivos=proyecto_archivos,
            terminal_context=terminal_context,
            asignatura=asignatura,
            perfil_alumno=perfil_alumno
        )

        async for event in agent_executor.astream_events({"messages": mensajes}, version="v2"):
            kind = event.get("event")
            
            # Emitir tokens del modelo a medida que van saliendo de Groq
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and chunk.content:
                    yield chunk.content

    except Exception as e:
        print(f"❌ [Tutor Stream] Error en streaming: {e}")
        yield f"\n[Error en generación: {str(e)}]"
    finally:
        _current_project_context.reset(token_context)
