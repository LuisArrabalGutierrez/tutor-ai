import os
import json
import re
import asyncio
from typing import Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

class PerfilAnalisis(BaseModel):
    carencia: str = Field(description="Concepto que el alumno no comprende o le cuesta, máx 5 palabras.")
    fortaleza: str = Field(description="Concepto que el alumno domina, máx 5 palabras.")

# Modelo rápido y económico para tareas de clasificación en segundo plano (Gemini 1M TPM o Groq)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")

analyst_llm = None
if GOOGLE_API_KEY:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        analyst_llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )
    except Exception as e:
        print(f"⚠️ [Analyst Init] Fallback a Groq: {e}")

if not analyst_llm and GROQ_API_KEY:
    analyst_llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model_name=GROQ_FAST_MODEL,
        temperature=0.1
    )

async def update_student_profile(user_id: str, messages: list, code: dict, supabase_client):
    """Analiza la última interacción del alumno para actualizar sus fortalezas y debilidades pedagógicas."""
    if not user_id or not messages or not supabase_client:
        return

    last_msg = messages[-1].get('content', '') if messages else ''
    if not last_msg or len(last_msg.strip()) < 5:
        return

    prompt = f"""Eres un evaluador pedagógico de programación C++ y Linux.
Tu objetivo es detectar qué concepto NO sabe el alumno (carencia) y qué concepto DOMINA (fortaleza).

Último mensaje del alumno:
"{last_msg}"

Instrucciones:
1. 'carencia': Si tiene dudas o errores conceptuales, nómbralo (máximo 5 palabras). Si no hay, pon 'Ninguna detectada'.
2. 'fortaleza': Si demuestra resolver o razonar bien un concepto, nómbralo (máximo 5 palabras). Si no hay, pon 'Ninguna detectada'.
3. Responde estrictamente con un objeto JSON: {{"carencia": "...", "fortaleza": "..."}}"""

    try:
        response = await analyst_llm.ainvoke(prompt)
        content = response.content.strip()

        # Extracción robusta de JSON mediante expresión regular
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
        else:
            data = {"carencia": "Ninguna detectada", "fortaleza": "Ninguna detectada"}

        carencia = data.get('carencia', 'Ninguna detectada')
        fortaleza = data.get('fortaleza', 'Ninguna detectada')

        # Si ambos son 'Ninguna detectada', no sobreescribimos con datos vacíos
        if carencia == "Ninguna detectada" and fortaleza == "Ninguna detectada":
            return

        def _update_db():
            update_payload = {}
            if carencia != "Ninguna detectada":
                update_payload["carencias"] = carencia
            if fortaleza != "Ninguna detectada":
                update_payload["fortalezas"] = fortaleza
            
            if update_payload:
                supabase_client.table("perfiles").update(update_payload).eq("id", user_id).execute()

        await asyncio.to_thread(_update_db)
        print(f"✅ [Analista] Perfil de usuario {user_id} actualizado.")

    except Exception as e:
        print(f"⚠️ [Analista] Error actualizando perfil pedagógico: {e}")
