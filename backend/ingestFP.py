import os
import glob
import time
from google import genai
from google.genai import types
from pypdf import PdfReader
from supabase import create_client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def limpiar_ruido(texto: str) -> str:
    lineas = texto.split('\n')
    lineas_limpias = []
    
    for l in lineas:
        l_lower = l.lower()
        # Filtros de ruido específicos para los PDFs de Fundamentos de Programación
        if any(ruido in l_lower for ruido in ["decsai", "ccia", "universidad de granada", "d. molina", "f.j. rodríguez", "page", "fundamentos de programación"]):
            continue
        if l.strip():
            lineas_limpias.append(l.strip())
            
    return "\n".join(lineas_limpias)

def ingest_slides(file_path: str, tema_principal: str):
    print(f"Iniciando: {tema_principal}")
    reader = PdfReader(file_path)
    
    for num_pag, page in enumerate(reader.pages):
        texto_raw = page.extract_text()
        if not texto_raw:
            continue
            
        texto_limpio = limpiar_ruido(texto_raw)
        
        # Ignorar páginas con contenido irrelevante o vacías
        if len(texto_limpio) < 40:
            continue

        contexto_enriquecido = f"Asignatura Fundamentos de Programación (FP) - {tema_principal}, Pag {num_pag + 1}:\n{texto_limpio}"

        try:
            # Generar embedding de 768 dimensiones
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=contexto_enriquecido,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768
                )
            )
            embedding = result.embeddings[0].values

            # Insertar en base de datos
            supabase.table("apuntes").insert({
                "tema": f"{tema_principal} - Pag {num_pag + 1}",
                "contenido": contexto_enriquecido,
                "embedding": embedding,
                #"asignatura": "FP"  para cuando cambie la insercion de la BD
            }).execute()
            
            print(f"  OK -> Pag {num_pag + 1}")
            
            # Rate limiting API Google
            time.sleep(2) 
            
        except Exception as e:
            print(f"  Error en Pag {num_pag + 1}: {e}")
            # Backoff en caso de saturación
            time.sleep(15) 

    print(f"Completado: {tema_principal}\n")

def procesar_carpeta(carpeta: str):
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print(f"Carpeta '{carpeta}' no existía. Creada.")
        return

    archivos_pdf = glob.glob(os.path.join(carpeta, "*.pdf"))
    if not archivos_pdf:
        print("No hay archivos PDF en el directorio.")
        return
        
    print(f"Archivos encontrados: {len(archivos_pdf)}. Iniciando proceso...\n" + "-"*40)
    
    for archivo in archivos_pdf:
        nombre_archivo = os.path.basename(archivo)
        tema = os.path.splitext(nombre_archivo)[0]
        ingest_slides(archivo, tema)

    print("Proceso de vectorización finalizado.")

if __name__ == "__main__":
    carpeta_apuntes = "apuntes_pdf/FP"
    procesar_carpeta(carpeta_apuntes)