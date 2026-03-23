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
    # Ruido exacto de las cabeceras/logos de MP
    ruido_conocido = [
        "METODOLOGÍA DE LA PROGRAMACIÓN",
        "GRADO EN INGENIERÍA INFORMÁTICA",
        "DECSAI",
        "TAS GRANA",
        "PLUS",
        "ULTRA",
        "1531"
    ]
    
    for ruido in ruido_conocido:
        texto = texto.replace(ruido, "")

    # Limpieza línea por línea para el ruido del IDE
    lineas = texto.split('\n')
    lineas_limpias = []
    
    for l in lineas:
        l_lower = l.lower()
        # Omitir líneas con ruido de ejecución del compilador/IDE
        if ("process returned" in l_lower or 
            "press any key" in l_lower or 
            "execution time" in l_lower):
            continue
            
        # Si la línea no se ha quedado vacía, la guardamos
        if l.strip() != "":
            lineas_limpias.append(l.strip())
            
    texto_limpio = "\n".join(lineas_limpias)
    
    # Limpiar los saltos de línea inmensos que deja el PDF
    texto_limpio = re.sub(r'\n{2,}', '\n', texto_limpio)
            
    return texto_limpio.strip()

def ingest_slides(file_path: str, tema_principal: str, diapositivas_subidas: set):
    print(f"\n Iniciando inyección: {tema_principal}")
    nombre_archivo = os.path.basename(file_path)
    reader = PdfReader(file_path)
    
    for num_pag, page in enumerate(reader.pages, start=1):
        # RESUME: Si esta página ya está en la BD, nos la saltamos
        if (nombre_archivo, num_pag) in diapositivas_subidas:
            continue

        texto_raw = page.extract_text()
        
        if not texto_raw:
            continue
            
        texto_limpio = limpiar_ruido(texto_raw)
        
        if len(texto_limpio) < 30:
            print(f"  Diapositiva {num_pag} descartada (sin contenido útil).")
            continue

        # Enriquecemos un poco el contexto para el vector (ayuda a Gemini a entender el bloque)
        contexto_enriquecido = f"Tema: {tema_principal}\n{texto_limpio}"

        # Bucle de reintento para evitar crasheos por el límite 429 de Google
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
                    "asignatura": "MP",         
                    "diapositiva": num_pag      
                }).execute()
                
                print(f"   Subida diapositiva {num_pag}...")
                exito = True
                time.sleep(1.5) 
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"   Límite de Google alcanzado. Pausando 45s en la diapo {num_pag}...")
                    time.sleep(45)
                else:
                    print(f"   Error en diapositiva {num_pag}: {e}")
                    exito = True 

    print(f"{tema_principal} completado")

def procesar_carpeta(carpeta: str):
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print(f" Creada la carpeta '{carpeta}'. Mete tus PDFs de MP dentro.")
        return

    archivos_pdf = glob.glob(os.path.join(carpeta, "*.pdf"))
    
    if not archivos_pdf:
        print(f" No hay archivos PDF en la carpeta {carpeta}.")
        return
        
    print("Comprobando diapositivas de MP ya existentes en la BD...")
    respuesta = supabase.table("apuntes").select("tema, diapositiva").eq("asignatura", "MP").execute()
    diapositivas_subidas = set((r["tema"], r["diapositiva"]) for r in respuesta.data)
    
    for archivo in archivos_pdf:
        tema = os.path.splitext(os.path.basename(archivo))[0]
        ingest_slides(archivo, tema, diapositivas_subidas)

    print("\n TODOS LOS APUNTES DE MP VECTORIZADOS")

if __name__ == "__main__":
    carpeta_apuntes = "apuntes_pdf/MP" 
    procesar_carpeta(carpeta_apuntes)