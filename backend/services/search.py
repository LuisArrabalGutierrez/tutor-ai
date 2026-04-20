import os
import urllib.parse
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

client_google = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def search_theory_logic(pregunta: str) -> str:
    try:
        # 1. Embedding
        result = client_google.models.embed_content(
            model="gemini-embedding-001",
            contents=pregunta,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
        )
        vector_pregunta = result.embeddings[0].values

        # 2. Búsqueda en Supabase
        respuesta = supabase.rpc( 
            'match_apuntes',
            {
                'query_embedding': vector_pregunta, 
                'match_threshold': 0.40, # Tolerancia media para encontrar más resultados
                'match_count': 3
            }
        ).execute()

        if not respuesta.data:
            return "No se ha encontrado este concepto en los apuntes. Guía al alumno con tus conocimientos generales."

        # 3. Formateo de salida
        mejor_match = respuesta.data[0]
        diap_mejor = mejor_match.get('diapositiva', 0)
        tema_mejor = mejor_match['tema']
        
        tema_mejor_limpio = tema_mejor[:-4] if tema_mejor.lower().endswith('.pdf') else tema_mejor
        nombre_archivo_url = urllib.parse.quote(f"{tema_mejor_limpio}.pdf")
        
        BASE_URL_STORAGE = "https://osalgrcicglnpajcocyt.supabase.co/storage/v1/object/public/apuntes"
        url_pdf = f"{BASE_URL_STORAGE}/{nombre_archivo_url}#page={diap_mejor}"
        
        # Devolvemos el enlace puro en la primera línea
        contexto = f"[{tema_mejor_limpio}.pdf - Diapositiva {diap_mejor}]({url_pdf})\n\n"
        contexto += "INFORMACIÓN EXTRAÍDA PARA TU EXPLICACIÓN:\n"
        for match in respuesta.data:
            contexto += f"- {match['contenido']}\n"
        
        return contexto

    except Exception as e:
        return f"Error en búsqueda en base de datos: {str(e)}"