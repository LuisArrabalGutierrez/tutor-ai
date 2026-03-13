import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from search import search_theory 
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
REGLA 1: NUNCA des la solución directa al código ni lo escribas corregido. El alumno debe llegar a ella razonando.
REGLA 2: Usa 'compiler_tool' SOLO para errores de código o fallos de ejecución. NO la uses para dudas de teoría pura.
REGLA 3: Si el alumno intenta responder a una pregunta socrática previa, valida su respuesta primero ("¡Correcto!", "Incorrecto" o "Casi") antes de mirar el código de fondo. Si es incorrecta, hazle pensar con otra pregunta relacionada. Si es correcta o casi, entonces mira el código para guiarle a la solución final. 
REGLA 4: CITAS OBLIGATORIAS: Si usas 'search_theory', DEBES incluir explícitamente el [ORIGEN] y la [SIMILITUD] en tu respuesta y asignatura. Ejemplo: "Como indica el [Tema 03 - Clases - Pag 5] de la asignatura de ( MP ) (Similitud: 68%)...". Si los apuntes no sirven, avisa: "No he encontrado esto en los apuntes oficiales, pero te explico:".
REGLA 5: ESTRUCTURA DE RESPUESTA TEÓRICA: 1. Valida (si aplica). 2. Nombra la diapositiva exacta y explica el concepto apoyándote en ella. 3. Termina SIEMPRE con una pregunta socrática relacionada para hacerle pensar. ¡No respondas solo con otra pregunta!
REGLA 6: Para errores de sintaxis en el código, no le digas la solución. Guía su vista (ej. "¿Qué carácter falta al final de la línea 8?").
REGLA 7: SOLO da la solución directa y completa si el alumno dice literalmente "me rindo" o "dame la solución".
REGLA 8: SIEMPRE termina tu respuesta con una pregunta socrática que invite al alumno a pensar y reflexionar sobre el tema, incluso después de resolver un error de código. Ejemplo: "Ahora que hemos corregido ese error, ¿puedes explicarme por qué era necesario ese cambio?".
REGLA 9: SALUDOS Y FUERA DE TEMA: Si el alumno saluda (ej. "hola") o habla de algo ajeno a la programación, sé educado y natural, pero redirige inmediatamente la conversación preguntando en qué puedes ayudarle con C++ o con su código actual."""


    mensajes = [SystemMessage(content=instrucciones)]

    # Cargar historial previo
    for msg in historial[:-1]:
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
    # Prueba rápida
    historial_prueba = [
        {"role": "user", "content": "Hola, tengo un error en mi código."},
    ]
    codigo_prueba = """#include <iostream>
                using namespace std;  """
    print(get_socratic_response(historial_prueba, codigo_prueba))