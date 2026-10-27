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

# --- INICIALIZACIÓN DEL LLM CON FALLBACK ---
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Modelo principal para razonamiento pedagógico
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name=GROQ_MODEL,
    temperature=0.3
)

# Modelo ultra-rápido para saludos y fallback ante rate limits (>800 tokens/segundo)
llm_fast = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name=GROQ_FAST_MODEL,
    temperature=0.2
)

# Compilación única del agente en memoria al arrancar el backend
agent_executor = create_react_agent(llm, tools=tutor_tools)


def _es_saludo_o_charla(pregunta: str) -> bool:
    """Detecta de forma instantánea (<0.01ms) si el mensaje es un saludo o cortesía básica."""
    if not pregunta:
        return True
    p = pregunta.strip().lower()
    palabras = p.split()
    if len(palabras) <= 5:
        saludos = [
            "hola", "buenas", "hey", "buenos dias", "buenas tardes", "buenas noches",
            "que tal", "cómo estás", "como estas", "ayuda", "saludos", "hola!", "hola buenas"
        ]
        if any(s in p for s in saludos):
            return True
    return False


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

    archivos_relevantes = {}
    total_len = 0
    if proyecto_archivos:
        for nombre, contenido in proyecto_archivos.items():
            if nombre.endswith(('.cpp', '.h', '.hpp', '.c', 'Makefile', 'makefile')):
                frag = contenido[:2500]
                archivos_relevantes[nombre] = frag
                total_len += len(frag)
                if total_len > 8000:
                    break
        contexto_archivos = json.dumps(archivos_relevantes, indent=2)
    else:
        contexto_archivos = "(Sin archivos en el proyecto)"

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
    """Genera la respuesta socrática completa con Fast-Path para saludos (latencia < 150ms)."""
    ultima_pregunta = historial[-1].get("content", "").strip() if historial else ""

    # FAST-PATH: Saludos directos ultra-rápidos
    if _es_saludo_o_charla(ultima_pregunta):
        try:
            materia = "Sistemas Unix/Linux" if asignatura == "linux" else "Programación en C++"
            rol_rapido = f"Eres el Tutor IA Socrático de la Universidad de Granada (UGR) para {materia}. Da una bienvenida cálida, cordial y breve (1-2 frases), invitando al alumno a plantear su duda."
            mensajes_rapidos = [SystemMessage(content=rol_rapido), HumanMessage(content=ultima_pregunta)]
            res = await llm_fast.ainvoke(mensajes_rapidos)
            return res.content
        except Exception as e_fast:
            print(f"⚠️ [Fast-Path Fallback]: {e_fast}")

    token_context = _current_project_context.set(proyecto_archivos or {})
    try:
        mensajes = _build_context_and_messages(
            historial=historial,
            proyecto_archivos=proyecto_archivos,
            terminal_context=terminal_context,
            asignatura=asignatura,
            perfil_alumno=perfil_alumno
        )
        try:
            respuesta = await agent_executor.ainvoke({"messages": mensajes})
            return respuesta["messages"][-1].content
        except Exception as e_agent:
            print(f"⚠️ [Agent Fallback a LLM Fast]: {e_agent}")
            res_fb = await llm_fast.ainvoke(mensajes)
            return res_fb.content
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
    """Transmite en streaming los tokens en tiempo real con Fast-Path para saludos instantáneos."""
    ultima_pregunta = historial[-1].get("content", "").strip() if historial else ""

    # FAST-PATH STREAM: Saludos comienzan a escribirse en pantalla en < 100ms con llm_fast
    if _es_saludo_o_charla(ultima_pregunta):
        try:
            materia = "Sistemas Unix/Linux" if asignatura == "linux" else "Programación en C++"
            rol_rapido = f"Eres el Tutor IA Socrático de la Universidad de Granada (UGR) para {materia}. Da una bienvenida cálida, cordial y breve (1-2 frases), invitando al alumno a plantear su duda."
            mensajes_rapidos = [SystemMessage(content=rol_rapido), HumanMessage(content=ultima_pregunta)]
            async for chunk in llm_fast.astream(mensajes_rapidos):
                if chunk.content:
                    yield chunk.content
            return
        except Exception as e_fast_stream:
            print(f"⚠️ [Fast-Path Stream Fallback]: {e_fast_stream}")

    token_context = _current_project_context.set(proyecto_archivos or {})
    try:
        mensajes = _build_context_and_messages(
            historial=historial,
            proyecto_archivos=proyecto_archivos,
            terminal_context=terminal_context,
            asignatura=asignatura,
            perfil_alumno=perfil_alumno
        )

        try:
            async for event in agent_executor.astream_events({"messages": mensajes}, version="v2"):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and chunk.content:
                        yield chunk.content
        except Exception as e_stream_agent:
            print(f"⚠️ [Stream Agent Fallback a Fast]: {e_stream_agent}")
            async for chunk in llm_fast.astream(mensajes):
                if chunk.content:
                    yield chunk.content

    except Exception as e:
        print(f"❌ [Tutor Stream] Error en streaming: {e}")
        yield f"\n[Error en generación: {str(e)}]"
    finally:
        _current_project_context.reset(token_context)
