import os
import glob
import time
from google import genai
from google.genai import types
from pypdf import PdfReader
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def limpiar_ruido(texto: str) -> str:
    lineas = texto.split('\n')
    lineas_limpias = []
    
    for l in lineas:
        l_lower = l.lower()
        if "decsai" in l_lower or "process returned" in l_lower or "press any key" in l_lower or "execution time" in l_lower:
            continue
        if l.strip() != "":
            lineas_limpias.append(l.strip())
            
    return "\n".join(lineas_limpias)

def ingest_slides(file_path: str, tema_principal: str):
    print(f"🚀 Iniciando inyección: {tema_principal}")
    reader = PdfReader(file_path)
    
    #lo que hacemos es embeber cada pagina para que cada vector tenga un contexto adecuado
    for num_pag, page in enumerate(reader.pages):
        texto_raw = page.extract_text()
        
        if not texto_raw:
            continue
            
        texto_limpio = limpiar_ruido(texto_raw)
        
        if len(texto_limpio) < 30:
            continue

        contexto_enriquecido = f"Asignatura de C++ - {tema_principal}, Diapositiva {num_pag + 1}:\n{texto_limpio}"

        try:
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=contexto_enriquecido,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768
                )
            )
            embedding = result.embeddings[0].values

            supabase.table("apuntes").insert({
                "tema": f"{tema_principal} - Pag {num_pag + 1}",
                "contenido": contexto_enriquecido,
                "embedding": embedding
            }).execute()
            
            print(f" Subida diapositiva {num_pag + 1}...")
            
            # Pausa de 2 segundos para no saturar la API
            time.sleep(2) 
            
        except Exception as e:
            print(f" Error en diapositiva {num_pag + 1}: {e}")
            # Si hay error esperamos antes de seguir
            time.sleep(15) 

    print(f"{tema_principal} completado\n")

def procesar_carpeta(carpeta: str):
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print(f" Creada la carpeta '{carpeta}'.")
        return

    archivos_pdf = glob.glob(os.path.join(carpeta, "*.pdf"))
    
    if not archivos_pdf:
        print(f" No hay archivos PDF.")
        return
        
    
    for archivo in archivos_pdf:
        nombre_archivo = os.path.basename(archivo)
        tema = os.path.splitext(nombre_archivo)[0]
        ingest_slides(archivo, tema)

    print("TODOS LOS APUNTES VECTORIZADOS")

if __name__ == "__main__":
    carpeta_apuntes = "apuntes_pdf"
    procesar_carpeta(carpeta_apuntes)