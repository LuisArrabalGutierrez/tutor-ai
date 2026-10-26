import os
import urllib.parse
import asyncio
from functools import lru_cache
from typing import Optional, Tuple
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Inicialización segura de clientes externos
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client_google = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

# Caché en memoria para evitar llamadas redundantes a la API de Embeddings de Google
@lru_cache(maxsize=512)
def _get_embedding_cached(texto: str) -> Optional[Tuple[float, ...]]:
    """Obtiene el embedding de la pregunta mediante Google GenAI con caché LRU."""
    if not client_google:
        return None
    try:
        result = client_google.models.embed_content(
            model="gemini-embedding-001",
            contents=texto,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
        )
        return tuple(result.embeddings[0].values)
    except Exception as e:
        print(f"⚠️ [RAG] Error al generar embedding con Google GenAI: {e}")
        return None

# Caché LRU de resultados de búsqueda completa para preguntas comunes
_RESULT_CACHE = {}
_MAX_RESULT_CACHE = 256

def search_theory_logic(pregunta: str) -> str:
    """
    Busca apuntes en Supabase (pgvector) a partir de la duda teórica del alumno.
    Utiliza caché en dos niveles (embedding y resultado) para latencia sub-milisegundo en preguntas frecuentes.
    """
    if not supabase:
        return "Base de datos no configurada. Guía al alumno con tus conocimientos generales."

    pregunta_limpia = pregunta.strip()
    clave_cache = pregunta_limpia.lower()

    if clave_cache in _RESULT_CACHE:
        return _RESULT_CACHE[clave_cache]

    try:
        # 1. Obtener Vector (Caché LRU integrada)
        vector_tuple = _get_embedding_cached(clave_cache)
        if not vector_tuple:
            return "No se pudo conectar con el servicio de teoría. Explica el concepto directamente con pedagogía socrática."

        vector_pregunta = list(vector_tuple)

        # 2. Búsqueda por similitud de coseno en Supabase (RPC match_apuntes con índice HNSW)
        respuesta = supabase.rpc(
            'match_apuntes',
            {
                'query_embedding': vector_pregunta,
                'match_threshold': 0.40,
                'match_count': 3
            }
        ).execute()

        if not respuesta.data:
            resultado_vacio = "No se ha encontrado este concepto exacto en los apuntes oficiales. Guía al alumno con tus conocimientos generales sin enlace."
            if len(_RESULT_CACHE) < _MAX_RESULT_CACHE:
                _RESULT_CACHE[clave_cache] = resultado_vacio
            return resultado_vacio

        # 3. Formateo de la diapositiva y el enlace Markdown
        mejor_match = respuesta.data[0]
        diap_mejor = mejor_match.get('diapositiva', 0)
        tema_mejor = mejor_match.get('tema', 'Apuntes')
        
        tema_mejor_limpio = tema_mejor[:-4] if tema_mejor.lower().endswith('.pdf') else tema_mejor
        nombre_archivo_url = urllib.parse.quote(f"{tema_mejor_limpio}.pdf")
        
        BASE_URL_STORAGE = "https://osalgrcicglnpajcocyt.supabase.co/storage/v1/object/public/apuntes"
        url_pdf = f"{BASE_URL_STORAGE}/{nombre_archivo_url}#page={diap_mejor}"
        
        # Enlace estricto en la primera línea para renderizado directo en React
        contexto = f"[{tema_mejor_limpio}.pdf - Diapositiva {diap_mejor}]({url_pdf})\n\n"
        contexto += "INFORMACIÓN EXTRAÍDA DE LOS APUNTES UGR:\n"
        for match in respuesta.data:
            contenido = match.get('contenido', '').strip()
            if contenido:
                contexto += f"- {contenido}\n"

        # Guardar en caché de resultados
        if len(_RESULT_CACHE) >= _MAX_RESULT_CACHE:
            _RESULT_CACHE.pop(next(iter(_RESULT_CACHE)))
        _RESULT_CACHE[clave_cache] = contexto

        return contexto

    except Exception as e:
        print(f"❌ [RAG] Error en búsqueda Supabase: {e}")
        return f"Error en búsqueda en base de datos: {str(e)}"

async def async_search_theory_logic(pregunta: str) -> str:
    """Wrapper no bloqueante para ejecutar la búsqueda RAG en un hilo del pool de asyncio."""
    return await asyncio.to_thread(search_theory_logic, pregunta)
