import os
import re
import sys
import json
import asyncio
import time
from contextvars import ContextVar
from typing import AsyncGenerator, Dict, List, Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from tutor_graph import build_tutor_graph

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(BACKEND_DIR, "mcp", "mcp_server.py")
MCP_RETRY_AFTER_S = 60

# ContextVar: proyecto del alumno de la petición en curso. El LLM no lo ve ni lo puede inventar;
# el adaptador de compilar_cpp lo inyecta como argumento de la herramienta MCP.
_current_project_context: ContextVar[Dict[str, str]] = ContextVar("current_project_context", default={})

# --- INICIALIZACIÓN MULTI-PROVEEDOR Y RESILIENCIA (1M TPM CON GEMINI + FALLBACK GROQ) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm_fast = None

# 1. Configuración de Groq (secundario o fast-fallback)
llm_groq = None
if GROQ_API_KEY:
    try:
        llm_groq = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.3
        )
        llm_fast = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=GROQ_FAST_MODEL,
            temperature=0.2
        )
    except Exception as e:
        print(f"⚠️ [Tutor Init] Error inicializando ChatGroq: {e}")

# 2. Configuración de Google Gemini (motor principal de alta capacidad: 1M TPM)
llm_gemini = None
if GOOGLE_API_KEY and ChatGoogleGenerativeAI:
    try:
        llm_gemini = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )
        if not llm_fast:
            llm_fast = llm_gemini
    except Exception as e:
        print(f"⚠️ [Tutor Init] Error inicializando Gemini: {e}")



# --- HERRAMIENTAS VÍA MCP ---------------------------------------------------------------------
# Las tools (buscar_apuntes_ugr, compilar_cpp, buscar_internet) viven en mcp/mcp_server.py, un
# proceso hijo por stdio que se mantiene vivo mientras corre la API. Un task dedicado es dueño de
# la sesión MCP para abrirla y cerrarla desde el mismo task (requisito de anyio).

class _Runtime:
    def __init__(self, loop):
        self.loop = loop
        self.primary = None
        self.fallback = None
        self.tools: list = []
        self.tool_names: List[str] = []
        self.mcp_ok = False
        self.graph_mode = False
        self.started_at = 0.0
        self.ready = asyncio.Event()
        self.stop = asyncio.Event()
        self.task: Optional[asyncio.Task] = None


_runtime: Optional[_Runtime] = None
_init_lock: Optional[asyncio.Lock] = None
_init_lock_loop = None


def _mcp_connection() -> dict:
    return {
        "tutor": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [MCP_SERVER_PATH],
            "cwd": BACKEND_DIR,
            # Pool propio del servidor MCP: nombres distintos a los del pool de /api/execute
            "env": {**os.environ, "WARM_POOL_PREFIX": "tutor_mcp_", "WARM_POOL_SIZE": os.getenv("MCP_POOL_SIZE", "2")},
        }
    }


def _adapt_tools(mcp_tools: list) -> list:
    """compilar_cpp pide el proyecto como argumento en el servidor MCP; al LLM se le ofrece sin
    parámetros y el proyecto sale del ContextVar de la petición."""
    tools = []
    for t in mcp_tools:
        if t.name != "compilar_cpp":
            tools.append(t)
            continue

        async def _compilar(_mcp_tool=t) -> str:
            archivos = _current_project_context.get()
            if not archivos:
                return "Error: No hay archivos de código en el proyecto actual."
            try:
                return _extract_text_content(await _mcp_tool.ainvoke({"archivos": archivos}))
            except Exception as e:
                return f"Error en sandbox de compilación: {str(e)}"

        tools.append(StructuredTool.from_function(coroutine=_compilar, name="compilar_cpp", description=t.description))
    return tools


def _graph_enabled() -> bool:
    """TUTOR_GRAPH=0 vuelve al agente prefabricado (create_react_agent), útil para comparar en las medidas."""
    return os.getenv("TUTOR_GRAPH", "1") != "0"


def _build_agents(rt: _Runtime, tools: list) -> None:
    rt.graph_mode = _graph_enabled()

    def _agente(llm):
        if rt.graph_mode:
            # El juez del guardrail usa el modelo rápido; si no hay, el propio modelo
            return build_tutor_graph(llm, tools, judge_llm=llm_fast or llm)
        return create_react_agent(llm, tools=tools)

    if llm_gemini:
        rt.primary = _agente(llm_gemini)
        if llm_groq:
            rt.fallback = _agente(llm_groq)
    elif llm_groq:
        rt.primary = _agente(llm_groq)


async def _mcp_runner(rt: _Runtime) -> None:
    tools: list = []
    try:
        client = MultiServerMCPClient(_mcp_connection())
        async with client.session("tutor") as session:
            tools = _adapt_tools(await load_mcp_tools(session))
            rt.tools = tools
            rt.tool_names = [t.name for t in tools]
            rt.mcp_ok = True
            _build_agents(rt, tools)
            rt.ready.set()
            await rt.stop.wait()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"⚠️ [MCP] No se pudo usar el servidor de herramientas: {e}", file=sys.stderr)
    finally:
        if not rt.ready.is_set():
            # Sin MCP el tutor sigue respondiendo, pero sin herramientas
            rt.mcp_ok = False
            _build_agents(rt, [])
            rt.ready.set()


async def start_tutor_runtime() -> None:
    """Arranca el servidor MCP y construye los agentes. Idempotente; se llama en el lifespan y, si hace falta, en la primera petición."""
    global _runtime, _init_lock, _init_lock_loop
    loop = asyncio.get_running_loop()
    if _init_lock is None or _init_lock_loop is not loop:
        _init_lock, _init_lock_loop = asyncio.Lock(), loop

    async with _init_lock:
        rt = _runtime
        if rt is not None and rt.loop is loop and rt.ready.is_set():
            if rt.mcp_ok or time.monotonic() - rt.started_at < MCP_RETRY_AFTER_S:
                return
            await _stop_runtime(rt)

        rt = _Runtime(loop)
        rt.started_at = time.monotonic()
        _runtime = rt
        rt.task = asyncio.create_task(_mcp_runner(rt))
        await rt.ready.wait()


async def _stop_runtime(rt: _Runtime) -> None:
    rt.stop.set()
    if rt.task and not rt.task.done():
        try:
            await asyncio.wait_for(rt.task, timeout=10)
        except Exception:
            rt.task.cancel()


async def stop_tutor_runtime() -> None:
    global _runtime
    rt, _runtime = _runtime, None
    if rt is not None and rt.loop is asyncio.get_running_loop():
        await _stop_runtime(rt)


async def _get_agents():
    await start_tutor_runtime()
    return _runtime.primary, _runtime.fallback



STREAM_CHUNK_CHARS = 60


def _log_guard(guard: dict) -> None:
    """Deja en stderr qué guardrails actuaron en la petición (solo si alguno lo hizo)."""
    activos = {k: v for k, v in guard.items() if v not in (False, 0, None) and k != "closing_question"}
    if activos:
        print(f"🛡️ [Guardrails] {activos}", file=sys.stderr, flush=True)


def _agent_input(mensajes: list, asignatura: str, consulta: str) -> dict:
    entrada = {"messages": mensajes}
    if _runtime is not None and _runtime.graph_mode:
        entrada.update(asignatura=asignatura, student_query=consulta)
    return entrada


async def _invoke_agent(agent, mensajes: list, asignatura: str, consulta: str) -> str:
    res = await agent.ainvoke(_agent_input(mensajes, asignatura, consulta))
    _log_guard(res.get("guard") or {})
    return _extract_text_content(res["messages"][-1].content)


async def _stream_agent(agent, mensajes: list, asignatura: str, consulta: str) -> AsyncGenerator[str, None]:
    if _runtime is not None and _runtime.graph_mode:
        # Con guardrails la respuesta se revisa completa antes de enviarla: se emite ya validada y troceada
        texto = await _invoke_agent(agent, mensajes, asignatura, consulta)
        for i in range(0, len(texto), STREAM_CHUNK_CHARS):
            yield texto[i:i + STREAM_CHUNK_CHARS]
        return
    async for event in agent.astream_events({"messages": mensajes}, version="v2"):
        if event.get("event") == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                texto = _extract_text_content(chunk.content)
                if texto:
                    yield texto


def _extract_text_content(content) -> str:
    """Extrae texto plano limpio compatible con strings directos y bloques de Gemini/OpenAI."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "".join(parts)
    return str(content) if content is not None else ""


# Vocabulario de cortesía: el fast-path solo se activa si TODAS las palabras del mensaje están aquí
_PALABRAS_SALUDO = frozenset({
    "hola", "holaa", "buenas", "buenos", "dias", "días", "tardes", "noches", "hey", "saludos",
    "que", "qué", "tal", "como", "cómo", "estas", "estás", "ayuda",
    "y", "a", "todos", "todas", "tutor",
})


def _es_saludo_o_charla(pregunta: str) -> bool:
    """True solo si el mensaje es un saludo puro (<= 5 palabras, todas de cortesía).

    "hola buenas tardes" es saludo; "hola, tengo un error" o "necesito ayuda con punteros" no,
    porque llevan palabras de contenido y deben pasar por el agente con herramientas.
    """
    if not pregunta:
        return True
    palabras = re.findall(r"[a-záéíóúüñ]+", pregunta.lower())
    if not palabras or len(palabras) > 5:
        return False
    return all(p in _PALABRAS_SALUDO for p in palabras)


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
4. CIERRE: Concluye siempre con una pregunta que guíe su próximo paso.
FORMATO: Responde solo en Markdown, nunca con etiquetas HTML. El único enlace permitido es el que devuelve 'buscar_apuntes_ugr'; no inventes ni escribas otras URLs."""
        texto_terminal = f"\n=== TERMINAL LINUX ===\n{terminal_context.strip()}" if terminal_context.strip() else ""
    else:
        rol_sistema = f"""Eres el Tutor Socrático de 'Metodología de la Programación' en C/C++ de la Universidad de Granada (UGR).{texto_perfil}
REGLAS SOCRÁTICAS ESTRICTAS:
0. SALUDOS: Si el alumno solo saluda o hace charla informal, responde breve y afable SIN herramientas.
1. TEORÍA: Si pregunta teoría o conceptos del temario, usa 'buscar_apuntes_ugr'.
2. CITAS OBLIGATORIAS: Si usas apuntes, la primera línea de tu respuesta DEBE ser el enlace Markdown: [tema.pdf - Diapositiva X](url).
3. COMPILADOR: Usa 'compilar_cpp' únicamente cuando el alumno lo solicite o haya un error de compilación.
4. NO DAR LA SOLUCIÓN DIRECTA: Corrige mediante pistas, analogías y preguntas reflexivas sobre el código.
5. CIERRE: Concluye siempre con una pregunta socrática.
FORMATO: Responde solo en Markdown, nunca con etiquetas HTML. El único enlace permitido es el que devuelve 'buscar_apuntes_ugr'; no inventes ni escribas otras URLs."""
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
    """Genera la respuesta socrática completa con Fast-Path para saludos y cascada de resiliencia."""
    ultima_pregunta = historial[-1].get("content", "").strip() if historial else ""

    # FAST-PATH: Saludos directos ultra-rápidos
    if _es_saludo_o_charla(ultima_pregunta) and llm_fast:
        try:
            materia = "Sistemas Unix/Linux" if asignatura == "linux" else "Programación en C++"
            rol_rapido = f"Eres el Tutor IA Socrático de la Universidad de Granada (UGR) para {materia}. Da una bienvenida cálida, cordial y breve (1-2 frases), invitando al alumno a plantear su duda."
            mensajes_rapidos = [SystemMessage(content=rol_rapido), HumanMessage(content=ultima_pregunta)]
            res = await llm_fast.ainvoke(mensajes_rapidos)
            return _extract_text_content(res.content)
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

        primary_agent, fallback_agent = await _get_agents()

        # 1. Intento con Agente Primario (Gemini / 1M TPM) con las herramientas MCP
        if primary_agent:
            try:
                return await _invoke_agent(primary_agent, mensajes, asignatura, ultima_pregunta)
            except Exception as e_primary:
                print(f"⚠️ [Tutor Fallback a Secundario]: Error en agente primario: {e_primary}")

        # 2. Intento con Agente Secundario (Fallback Groq)
        if fallback_agent:
            try:
                return await _invoke_agent(fallback_agent, mensajes, asignatura, ultima_pregunta)
            except Exception as e_fallback:
                print(f"⚠️ [Tutor Fallback a LLM Fast]: Error en agente secundario: {e_fallback}")

        # 3. Fallback directo a llm_fast
        if llm_fast:
            res_fb = await llm_fast.ainvoke(mensajes)
            return _extract_text_content(res_fb.content)

        return "Disculpa, el servicio de tutoría no está disponible en este momento."
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
    """Transmite en streaming los tokens en tiempo real con Fast-Path y tolerancia a fallos multi-proveedor."""
    ultima_pregunta = historial[-1].get("content", "").strip() if historial else ""

    # FAST-PATH STREAM: Saludos comienzan a escribirse en pantalla en < 100ms
    if _es_saludo_o_charla(ultima_pregunta) and llm_fast:
        try:
            materia = "Sistemas Unix/Linux" if asignatura == "linux" else "Programación en C++"
            rol_rapido = f"Eres el Tutor IA Socrático de la Universidad de Granada (UGR) para {materia}. Da una bienvenida cálida, cordial y breve (1-2 frases), invitando al alumno a plantear su duda."
            mensajes_rapidos = [SystemMessage(content=rol_rapido), HumanMessage(content=ultima_pregunta)]
            async for chunk in llm_fast.astream(mensajes_rapidos):
                texto = _extract_text_content(chunk.content)
                if texto:
                    yield texto
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

        streamed_any = False
        primary_agent, fallback_agent = await _get_agents()

        # 1. Stream con Agente Primario (Gemini / 1M TPM) con las herramientas MCP
        if primary_agent:
            try:
                async for texto in _stream_agent(primary_agent, mensajes, asignatura, ultima_pregunta):
                    streamed_any = True
                    yield texto
                return
            except Exception as e_stream_primary:
                print(f"⚠️ [Stream Primary Fallback a Secundario]: {e_stream_primary}")

        # 2. Si falló el primario sin haber emitido nada, intentar con el Secundario (Fallback Groq)
        if not streamed_any and fallback_agent:
            try:
                async for texto in _stream_agent(fallback_agent, mensajes, asignatura, ultima_pregunta):
                    streamed_any = True
                    yield texto
                return
            except Exception as e_stream_sec:
                print(f"⚠️ [Stream Secundario Fallback a Fast]: {e_stream_sec}")

        # 3. Si ambos fallaron antes de emitir, fallback directo a llm_fast
        if not streamed_any and llm_fast:
            async for chunk in llm_fast.astream(mensajes):
                texto = _extract_text_content(chunk.content)
                if texto:
                    yield texto

    except Exception as e:
        print(f"❌ [Tutor Stream] Error en streaming: {e}")
        yield f"\n[Error en generación: {str(e)}]"
    finally:
        _current_project_context.reset(token_context)
