import os
import glob
import time
import re
from google import genai
from google.genai import types
from pypdf import PdfReader
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def limpiar_ruido(texto: str) -> str:
    # cadenas a eliminar
    ruido_conocido = [
        "Fundamentos del Software",
        "Prácticas de Fundamentos del Software",
        "Lenguajes y Sistemas Informáticos",
        "Universidad de Granada",
        "Grado en Ingeniería Informática y",
        "Doble Grado en Ingeniería Informática y Matemáticas",
        "Doble Grado en Ingeniería Informática y Administración de Empresas",
        "Departamento de Lenguajes y Sistemas Informáticos",
        "E.T.S. Ingenierías Informática y de Telecomunicación"
    ]
    
    for ruido in ruido_conocido:
        texto = texto.replace(ruido, "")

    lineas = texto.split('\n')
    lineas_limpias = []
    
    for l in lineas:
        l_lower = l.lower()
        if ("process returned" in l_lower or 
            "press any key" in l_lower or 
            "execution time" in l_lower):
            continue
            
        if l.strip() != "":
            lineas_limpias.append(l.strip())
            
    texto_limpio = "\n".join(lineas_limpias)
    
    # quita saltos extra
    texto_limpio = re.sub(r'\n{2,}', '\n', texto_limpio)
            
    return texto_limpio.strip()

def ingest_slides(file_path: str, tema_principal: str, diapositivas_subidas: set):
    print(f"\nIniciando inyección: {tema_principal}")
    nombre_archivo = os.path.basename(file_path)
    reader = PdfReader(file_path)
    
    for num_pag, page in enumerate(reader.pages, start=1):
        # salta si ya esta procesada
        if (nombre_archivo, num_pag) in diapositivas_subidas:
            continue

        texto_raw = page.extract_text()
        
        if not texto_raw:
            continue
            
        texto_limpio = limpiar_ruido(texto_raw)
        
        if len(texto_limpio) < 30:
            print(f"  Página {num_pag} descartada")
            continue

        contexto_enriquecido = f"Tema: {tema_principal}\n{texto_limpio}"

        exito = False
        while not exito:
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
                    "tema": nombre_archivo,
                    "contenido": texto_limpio,
                    "embedding": embedding,
                    "asignatura": "FS",         
                    "diapositiva": num_pag      
                }).execute()
                
                print(f"   Subida página {num_pag}")
                exito = True
                time.sleep(1.5) 
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"   Límite alcanzado. Pausa de 45s en página {num_pag}")
                    time.sleep(45)
                else:
                    print(f"   Error en página {num_pag}: {e}")
                    exito = True 

    print(f"{tema_principal} completado")

def procesar_carpeta(carpeta: str):
    # crea carpeta si no existe
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print(f"Carpeta creada: {carpeta}")
        return

    archivos_pdf = glob.glob(os.path.join(carpeta, "*.pdf"))
    
    if not archivos_pdf:
        print(f"Sin PDFs en {carpeta}")
        return
        
    print("Comprobando registros en BD...")
    respuesta = supabase.table("apuntes").select("tema, diapositiva").eq("asignatura", "FS").execute()
    diapositivas_subidas = set((r["tema"], r["diapositiva"]) for r in respuesta.data)
    
    for archivo in archivos_pdf:
        tema = os.path.splitext(os.path.basename(archivo))[0]
        ingest_slides(archivo, tema, diapositivas_subidas)

    print("\nPROCESO TERMINADO")

if __name__ == "__main__":
    carpeta_apuntes = "apuntes_pdf/FS" 
    procesar_carpeta(carpeta_apuntes)