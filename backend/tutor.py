import os
import json
import sys
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv()

# Inicia LLM
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    #model_name="llama-3.3-70b-versatile" 
    #model_name="llama-3.1-8b-instant"
    #model_name="openai/gpt-oss-120b"
    model_name="deepseek-r1-distill-llama-70b"
    #model_name="mixtral-8x7b-32768"

)

async def get_socratic_response_async(
    historial: list, 
    proyecto_archivos: dict, 
    terminal_context: str = "", 
    asignatura: str = "cpp",
    perfil_alumno: dict = None 
) -> str:
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Guarda proyecto temporal para las herramientas MCP
    ruta_json = os.path.join(base_dir, "temp_project.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(proyecto_archivos, f)
        
    mcp_server_path = os.path.join(base_dir, "mcp/mcp_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[mcp_server_path] 
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)
            agent_executor = create_react_agent(llm, tools=mcp_tools)            
            
            # --- CONSTRUCCIÓN DEL BLOQUE DE PERFIL ADAPTATIVO ---
            texto_perfil = ""
            if perfil_alumno:
                fortalezas = perfil_alumno.get('fortalezas', 'Pendiente de analizar')
                carencias = perfil_alumno.get('carencias', 'Pendiente de analizar')
                
                texto_perfil = f"""
                === PERFIL FORMATIVO DEL ALUMNO (PERSONALIZACIÓN) ===
                - Fortalezas: {fortalezas}
                - Carencias/Debilidades: {carencias}
                
                INSTRUCCIÓN PEDAGÓGICA: Utiliza esta información para ajustar tu nivel de dificultad. 
                Si tiene carencias en un concepto que aparece en su código, sé más incisivo con preguntas socráticas sobre ese tema. 
                Si domina algo, no te detengas demasiado ahí.
                """

            # Configuración según asignatura
            if asignatura == "linux":
                rol_sistema = f"Eres un profesor estricto pero justo de 'Sistemas y Órdenes Unix' de la Universidad de Granada (UGR).\n{texto_perfil}"
                reglas_especificas = """
                        REGLAS ESTRICTAS (LINUX):
                        0. CONVERSACION: Si el alumno solo saluda responde de forma conversacional SIN herramientas.
                        1. BÚSQUEDA OBLIGATORIA: Si pregunta teoría, usa 'buscar_apuntes_ugr'.
                        2. PROHIBIDO PARAFRASEAR ENLACES: Tu respuesta DEBE empezar con el enlace Markdown.
                        3. ENFOQUE BASH: Enseña bash, permisos, tuberías y administración.
                        4. MÉTODO SOCRÁTICO: No des el comando exacto. Guíale.
                        5. CIERRE: Termina siempre con una pregunta que guíe su próximo paso."""

                if terminal_context.strip():
                    texto_terminal = f"\n\n=== CONTEXTO DE LA TERMINAL ===\n{terminal_context}"
                else:
                    texto_terminal = "\n\n=== CONTEXTO DE LA TERMINAL ===\n(Terminal vacía)"
                    
            else:
                rol_sistema = f"Eres un tutor socrático de 'Metodología de la Programación' en C/C++ de la Universidad de Granada (UGR).\n{texto_perfil}"
                reglas_especificas = """
                        REGLAS ESTRICTAS (C++):
                        0. CONVERSACION: Si el alumno solo saluda, responde normalmente SIN herramientas.
                        1. BÚSQUEDA OBLIGATORIA: Para teoría, usa 'buscar_apuntes_ugr'. 
                        2. CITAS CLICABLES: Tu respuesta DEBE EMPEZAR con el enlace [texto](url).
                        3. ANTI-BUCLE: Responde a la ÚLTIMA pregunta.
                        4. COMPILADOR: Usa 'compilar_cpp' SOLO si hay errores.
                        5. CIERRE: Termina siempre con una pregunta socrática."""
                texto_terminal = "" 

            # Construcción de la memoria de la conversación
            MAX_MENSAJES = 10
            historial_recortado = historial[-MAX_MENSAJES:] if len(historial) > MAX_MENSAJES else historial
            
            mensajes = [SystemMessage(content=rol_sistema)]
            
            for msg in historial_recortado[:-1]:
                if msg["role"] == "user":
                    mensajes.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    mensajes.append(AIMessage(content=msg["content"]))
                    
            archivos_json = json.dumps(proyecto_archivos, indent=2)
            if len(archivos_json) > 15000:
                archivos_json = archivos_json[:15000] + "\n\n... [TRUNCADO] ..."
                
            # Prompt Final con Contexto
            estado_actual = f"""=== ARCHIVOS DEL PROYECTO ACTUAL === 
                {archivos_json} 
                {texto_terminal}  

                === REGLAS RECORDATORIO === 
                {reglas_especificas} 

                === PREGUNTA DEL ALUMNO ===
                {historial[-1]['content']}

                [RECORDATORIO CRÍTICO]: 
                - Si el alumno saluda, responde sin herramientas.
                - Si hay enlace de apuntes, ponlo al PRINCIPIO de la respuesta."""

            mensajes.append(HumanMessage(content=estado_actual))

            try:
                respuesta = await agent_executor.ainvoke({"messages": mensajes})
                return respuesta["messages"][-1].content
            except Exception as e:
                return f"Error interno del agente: {e}"