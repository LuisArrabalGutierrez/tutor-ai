import os
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

client_google = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def buscar_contexto(pregunta: str) -> str:
    try:
        result = client_google.models.embed_content(
            model="gemini-embedding-001",
            contents=pregunta,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
        )
        vector_pregunta = result.embeddings[0].values

        respuesta = supabase.rpc(
            'match_apuntes',
            {
                'query_embedding': vector_pregunta, 
                'match_threshold': 0.20, 
                'match_count': 3
            }
        ).execute()

        if not respuesta.data:
            return ""

        contexto = ""
        for match in respuesta.data:
            similitud = match['similarity'] * 100
            # Metadatos para las citas del LLM
            contexto += f"[ORIGEN: {match['tema']} | SIMILITUD: {similitud:.1f}%]\n{match['contenido']}\n\n"
        
        return contexto

    except Exception as e:
        print(f"Error BD: {e}")
        return ""