import json
from langchain_groq import ChatGroq

# Modelo para analisis
analyst_llm = ChatGroq(model_name="llama-3.1-8b-instant")

async def update_student_profile(user_id: str, messages: list, code: dict, supabase_client):
    last_msg = messages[-1]['content']
    
    # Prompt mejorado sin ejemplos literales
    prompt = f"""
    Eres un evaluador pedagógico. Tu misión es detectar QUÉ NO SABE el alumno y QUÉ DOMINA.
    CONVERSACIÓN: {last_msg}

    INSTRUCCIONES:
    1. Si el alumno admite no saber algo, regístralo en 'carencia'.
    2. Si el alumno NO demuestra dominar nada en este mensaje, el valor de 'fortaleza' DEBE SER el anterior pasado. No inventes datos.
    3. Sé breve (máximo 5 palabras por campo).

    Responde SOLO con este formato JSON: {{"carencia": "...", "fortaleza": "..."}}
    """
    
    try:
        response = await analyst_llm.ainvoke(prompt)
        content = response.content
        
        # Limpiar markdown
        content = content.replace("```json", "").replace("```", "").strip()
        
        # Extraer JSON
        start = content.find('{{')
        end = content.rfind('}}')
        if start != -1 and end != -1:
            # Reemplazo de dobles llaves para el parsing correcto
            json_str = content[start:end+2].replace("{{", "{").replace("}}", "}")
            try:
                data = json.loads(json_str)
            except:
                data = json.loads(content[start:end+1])
        else:
            data = json.loads(content)
            
        # Guardar DB
        supabase_client.table("perfiles").update({
            "fortalezas": data.get('fortaleza', 'Ninguna detectada'),
            "carencias": data.get('carencia', 'Ninguna detectada')
        }).eq("id", user_id).execute()
        
    except Exception as e:
        print(f"ERROR EN ANALISTA: {e}")