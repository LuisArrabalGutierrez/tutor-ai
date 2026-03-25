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
    #model_name="llama-3.1-8b-instant" 
    model_name="llama-3.3-70b-versatile"

)

instrucciones = """Eres un tutor socrático de C++.

REGLAS ESTRICTAS:
1. BÚSQUEDA OBLIGATORIA [¡CRÍTICO!]: Si el alumno pregunta "dónde está", "temario", "diapositiva", o teoría, ESTÁS OBLIGADO a usar 'buscar_apuntes_ugr'. 
2. CITA EXACTA: La primera línea de la herramienta te dará una recomendación natural. TU RESPUESTA DEBE EMPEZAR COPIANDO ESA LÍNEA EXACTAMENTE.
3. ANTI-BUCLE: Responde SIEMPRE a la ÚLTIMA pregunta del alumno. NUNCA repitas literalmente una respuesta que ya hayas dado antes.
4. EXPLICACIÓN: Explica el concepto usando SOLO el texto proporcionado por la herramienta.
5. IGNORAR CÓDIGO: Si la pregunta es teórica, no analices el código del proyecto.
6. COMPILADOR: Usa 'compilar_cpp' SOLO si hay errores de código.
7. CIERRE: Termina siempre con una pregunta socrática."""

async def get_socratic_response_async(historial: list, proyecto_archivos: dict) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Guarda proyecto temporal
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
            
            MAX_MENSAJES = 10
            historial_recortado = historial[-MAX_MENSAJES:] if len(historial) > MAX_MENSAJES else historial
            
            mensajes = [SystemMessage(content="Eres un tutor de C++.")]
            
            for msg in historial_recortado[:-1]:
                if msg["role"] == "user":
                    mensajes.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    mensajes.append(AIMessage(content=msg["content"]))
                    
            archivos_json = json.dumps(proyecto_archivos, indent=2)
            
            # Trunca json si es muy largo
            if len(archivos_json) > 15000:
                archivos_json = archivos_json[:15000] + "\n\n... [TRUNCADO] ..."
                
            # Añade contexto y reglas al final
            estado_actual = f"""=== ARCHIVOS DEL PROYECTO ACTUAL ===\n{archivos_json}\n\n=== REGLAS RECORDATORIO ===\n{instrucciones}\n\n=== PREGUNTA DEL ALUMNO ===\n{historial[-1]['content']}"""

            mensajes.append(HumanMessage(content=estado_actual))

            try:
                respuesta = await agent_executor.ainvoke({"messages": mensajes})
                return respuesta["messages"][-1].content
            except Exception as e:
                return f"Error: {e}"