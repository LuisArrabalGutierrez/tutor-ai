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
        # 1. Obtener vector de la pregunta
        result = client_google.models.embed_content(
            model="gemini-embedding-001",
            contents=pregunta,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
        )
        vector_pregunta = result.embeddings[0].values

        # 2. Buscar en Supabase
        respuesta = supabase.rpc( 
            'match_apuntes',
            {
                'query_embedding': vector_pregunta, 
                'match_threshold': 0.20, 
                'match_count': 3
            }
        ).execute()

        if not respuesta.data:
            return "No hay apuntes sobre esto."

        mejor_match = respuesta.data[0]
        diap_mejor = mejor_match.get('diapositiva', 0)
        tema_mejor = mejor_match['tema']
        
        # Limpieza para evitar el .pdf.pdf
        tema_mejor_limpio = tema_mejor[:-4] if tema_mejor.lower().endswith('.pdf') else tema_mejor

        # Encode para URL (maneja espacios y tildes correctamente)
        nombre_archivo_url = urllib.parse.quote(f"{tema_mejor_limpio}.pdf")
        
        # URL FINAL: Directo al bucket 'apuntes' sin carpetas intermedias
        BASE_URL_STORAGE = "https://osalgrcicglnpajcocyt.supabase.co/storage/v1/object/public/apuntes"
        url_pdf = f"{BASE_URL_STORAGE}/{nombre_archivo_url}#page={diap_mejor}"
        
        # INSTRUCCIÓN AGRESIVA: Obligamos a la IA a no saludar y pegar el link primero
        contexto = "REGLA DE ORO: Empieza tu respuesta copiando EXACTAMENTE esta línea:\n"
        contexto += f"[{tema_mejor_limpio}.pdf - Diapositiva {diap_mejor}]({url_pdf})\n\n"
        
        contexto += "CONTENIDO EXTRAÍDO (Úsalo para tu explicación socrática):\n"
        for match in respuesta.data:
            contexto += f"- {match['contenido']}\n\n"
        
        return contexto

    except Exception as e:
        print(f"Error en búsqueda: {e}")
        return f"Error: {e}"