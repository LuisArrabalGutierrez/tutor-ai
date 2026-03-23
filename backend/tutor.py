import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from services.search import search_theory 
from services.compiler import compiler_tool

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

tools = [search_theory, compiler_tool]

# Inicializar agente
agent_executor = create_react_agent(llm, tools)

def get_socratic_response(historial: list, codigo: str) -> str:
    instrucciones = """Eres un tutor socrático de C++ en la universidad.

REGLA 1: NUNCA des la solución directa al código ni lo escribas corregido.
REGLA 2: Usa 'compiler_tool' SOLO para errores de código o fallos de ejecución.
REGLA 3: VALIDACIÓN: Si el alumno responde a una pregunta que TÚ le hiciste antes, valida su respuesta ("¡Correcto!", "Casi"). Si el alumno hace una PREGUNTA NUEVA, NO valides nada, simplemente respóndele. Ignora el código de fondo si la pregunta es teórica.
REGLA 4: USO DE BÚSQUEDA OBLIGATORIO: Para cualquier pregunta sobre conceptos, teoría o "temas", ESTÁS OBLIGADO a usar la herramienta 'search_theory' ANTES de contestar. PROHIBIDO inventar citas o porcentajes. Si usas la herramienta, cita literalmente: "[ASIGNATURA], [ORIGEN] (Diapositiva [DIAPOSITIVA]) - Similitud: [SIMILITUD]". Si no hay resultados, di: "No está en los apuntes, pero te explico:".
REGLA 5: ESTRUCTURA TEÓRICA: 1. Valida (SOLO si aplica). 2. Cita la asignatura, tema y diapositiva exacta y explica el concepto basándote estrictamente en el contenido recuperado. 3. Termina SIEMPRE con una pregunta socrática relacionada.
REGLA 6: Para errores de sintaxis, no des la solución. Guía su vista (ej. "¿Qué falta en la línea 8?").
REGLA 7: SOLO da la solución directa si el alumno dice literalmente "me rindo" o "dame la solución".
REGLA 8: SIEMPRE termina tu respuesta con una pregunta socrática que invite a reflexionar.
REGLA 9: OFF-TOPIC: Si el alumno saluda o se desvía del tema, redirige amablemente hacia C++."""
    mensajes = [SystemMessage(content=instrucciones)]

    # LIMITAR HISTORIAL: Nos quedamos solo con los últimos 10 mensajes (para no saturar la API)
    MAX_MENSAJES = 10
    historial_recortado = historial[-MAX_MENSAJES:] if len(historial) > MAX_MENSAJES else historial

    # Cargar historial previo recortado
    for msg in historial_recortado[:-1]:
        if msg["role"] == "user":
            mensajes.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            mensajes.append(AIMessage(content=msg["content"]))

    # Adjuntar el ultimo mensaje junto al codigo del editor
    ultima_pregunta = historial[-1]["content"]
    mensajes.append(HumanMessage(content=f"Codigo:\n{codigo}\nPregunta:\n{ultima_pregunta}"))

    try:
        response = agent_executor.invoke({"messages": mensajes})
        
        # Mostrar rastro en consola
        print("\n--- RASTRO DEL AGENTE ---")
        for m in response["messages"]:
            m.pretty_print()
        print("-------------------------\n")
        
        return response["messages"][-1].content
        
    except Exception as e:
        return f"Error IA: {e}"

if __name__ == "__main__":
    historial_prueba = [
        {"role": "user", "content": "Hola, tengo un error en mi código."},
    ]
    codigo_prueba = """#include <iostream>
                using namespace std;  """
    print(get_socratic_response(historial_prueba, codigo_prueba))