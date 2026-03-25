import os
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

client_google = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def search_theory_logic(pregunta: str) -> str:
    try:
        # Obtiene vector
        result = client_google.models.embed_content(
            model="gemini-embedding-001",
            contents=pregunta,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
        )
        vector_pregunta = result.embeddings[0].values

        # Busca en bd
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

        # Extrae el mejor resultado
        mejor_match = respuesta.data[0]
        similitud_mejor = mejor_match['similarity'] * 100
        asignatura_mejor = mejor_match.get('asignatura', 'Desconocida')
        diap_mejor = mejor_match.get('diapositiva', 0)
        
        # Formatea recomendacion sin etiquetas
        contexto = f"Te recomiendo encarecidamente revisar la diapositiva {diap_mejor} del PDF **{mejor_match['tema']}** de la asignatura {asignatura_mejor} (Similitud: {similitud_mejor:.1f}%).\n\n"
        
        contexto += "CONTENIDO DE LOS APUNTES:\n"
        
        for match in respuesta.data:
            contexto += f"- [{match.get('asignatura', 'N/A')}] {match['contenido']}\n\n"
        
        return contexto

    except Exception as e:
        print(f"Error: {e}")
        return f"Error interno al buscar en los apuntes: {e}"