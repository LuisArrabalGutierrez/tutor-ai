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

# Inicia LLM (Cambiado al modelo 8B instant para que no te quedes sin tokens)
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant" 
    # model_name="llama-3.3-70b-versatile" 
    )

async def get_socratic_response_async(
    historial: list, 
    proyecto_archivos: dict, 
    terminal_context: str = "", 
    asignatura: str = "cpp"
) -> str:
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Guarda proyecto temporal para que las herramientas MCP lo lean
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
            
            # --- 1. CONFIGURACIÓN DUAL DE IA (LINUX VS C++) ---
            if asignatura == "linux":
                rol_sistema = "Eres un profesor estricto pero justo de 'Sistemas y Órdenes Unix' de la Universidad de Granada (UGR)."
                reglas_especificas = """
REGLAS ESTRICTAS (LINUX):
1. BÚSQUEDA OBLIGATORIA: Si el alumno pregunta por teoría o diapositivas, usa 'buscar_apuntes_ugr'.
2. CITAS CLICABLES [¡CRÍTICO!]: La herramienta te dará un enlace Markdown en la primera línea. TU PRIMERA PALABRA DEBE SER ESE ENLACE. Tienes terminantemente prohibido saludar o introducir la respuesta. Pega el enlace [texto](url) y luego explica.
3. ENFOQUE BASH: Tu objetivo es enseñar bash, permisos de archivos, tuberías y administración de Linux.
4. MÉTODO SOCRÁTICO: NUNCA des el comando exacto al primer intento (ej. no digas 'usa chmod 755'). Guíale para que deduzca qué herramienta o flag usar leyendo el manual.
5. CONTEXTO VISUAL: El alumno te pasará lo que está viendo en su consola. Úsalo para corregirle si ves errores de "Permission denied" o "command not found".
6. CIERRE: Termina siempre con una pregunta que guíe su próximo paso."""
                
                # Preparamos el inyector de la terminal
                texto_terminal = ""
                if terminal_context.strip():
                    texto_terminal = f"\n\n=== CONTEXTO DE LA TERMINAL (LO QUE VE EL ALUMNO AHORA) ===\n{terminal_context}"
                else:
                    texto_terminal = "\n\n=== CONTEXTO DE LA TERMINAL ===\n(La terminal está vacía o el alumno acaba de entrar)"
                    
            else:
                rol_sistema = "Eres un tutor socrático de 'Metodología de la Programación' en C/C++ de la Universidad de Granada (UGR)."
                reglas_especificas = """
REGLAS ESTRICTAS (C++):
1. BÚSQUEDA OBLIGATORIA [¡CRÍTICO!]: Si el alumno pregunta "dónde está", "temario", "diapositiva", o teoría, ESTÁS OBLIGADO a usar 'buscar_apuntes_ugr'. 
2. CITAS CLICABLES [¡CRÍTICO!]: La herramienta te dará un enlace Markdown en la primera línea. TU PRIMERA PALABRA DEBE SER ESE ENLACE. Tienes terminantemente prohibido saludar o introducir la respuesta. Pega el enlace [texto](url) y luego da tu explicación.
3. ANTI-BUCLE: Responde SIEMPRE a la ÚLTIMA pregunta del alumno. NUNCA repitas literalmente una respuesta anterior.
4. EXPLICACIÓN: Explica el concepto usando SOLO el texto proporcionado por la herramienta.
5. COMPILADOR: Usa 'compilar_cpp' SOLO si hay errores de código.
6. CIERRE: Termina siempre con una pregunta socrática."""
                texto_terminal = "" # En C++ limpiamos la terminal para que no se distraiga con bash

            # --- 2. CONSTRUCCIÓN DEL HISTORIAL ---
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
                
            # --- 3. PROMPT MAESTRO ---
            estado_actual = f"""=== ARCHIVOS DEL PROYECTO ACTUAL ===
{archivos_json}
{texto_terminal}

=== REGLAS RECORDATORIO ===
{reglas_especificas}

=== PREGUNTA DEL ALUMNO ===
{historial[-1]['content']}"""

            mensajes.append(HumanMessage(content=estado_actual))

            # --- 4. EJECUCIÓN ---
            try:
                respuesta = await agent_executor.ainvoke({"messages": mensajes})
                return respuesta["messages"][-1].content
            except Exception as e:
                return f"Error interno del agente: {e}"