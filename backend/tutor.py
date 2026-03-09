import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from search import buscar_contexto 

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

def get_socratic_response(pregunta: str, codigo: str) -> str:
    contexto = buscar_contexto(pregunta)
    
    instrucciones_base = """Eres un tutor universitario de C++.
Sigue estas reglas ESTRICTAMENTE:
1. Analiza <codigo> y <pregunta>.
2. Si la pregunta es TEÓRICA, explícalo de forma directa y sencilla.
3. Si es un ERROR en el <codigo>, NO des la solución directa. Haz preguntas reflexivas.
4. Si el alumno se rinde o pide la solución explícitamente, dásela paso a paso.
5. REGLA DE CITAS: Si usas la <teoria> proporcionada, añade OBLIGATORIAMENTE al final de tu respuesta: 'A parte de esta solución, busca en la diapositiva X del tema Y. Coincide en un Z% con lo que he sacado de los apuntes.' Sustituye X, Y, Z con los datos extraídos de las etiquetas [ORIGEN] y [SIMILITUD]."""

    if contexto != "":
        instrucciones_completas = f"{instrucciones_base}\n\nResponde basándote ÚNICAMENTE en esta teoría:\n<teoria>\n{{contexto_teoria}}\n</teoria>"
    else:
        instrucciones_completas = f"{instrucciones_base}\n\nNo hay apuntes sobre esto. Empieza tu respuesta diciendo OBLIGATORIAMENTE: 'No he encontrado esto en los apuntes oficiales de la asignatura, pero te explico:'\n<teoria>\n{{contexto_teoria}}\n</teoria>"

    prompt = ChatPromptTemplate.from_messages([
        ("system", instrucciones_completas),
        ("user", "<codigo>\n{codigo_del_alumno}\n</codigo>\n\n<pregunta>\n{pregunta_del_alumno}\n</pregunta>")
    ])

    chain = prompt | llm

    try:
        response = chain.invoke({
            "contexto_teoria": contexto,
            "codigo_del_alumno": codigo,
            "pregunta_del_alumno": pregunta
        })
        return response.content
    except Exception as e:
        return f"Error IA: {e}"

if __name__ == "__main__":
    codigo_prueba = "class Animal {}; \nclass Perro : public Animal {};"
    pregunta_prueba = "He creado esta clase pero no sé qué es la herencia, ¿me lo explicas?"
    
    print(get_socratic_response(pregunta_prueba, codigo_prueba))