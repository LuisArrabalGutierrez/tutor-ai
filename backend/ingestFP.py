import os
import time
import re
import PyPDF2
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

client_google = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

CARPETA_PDFS = "./apuntes_pdf/FP"

def limpiar_texto(texto: str) -> str:
    """Limpia el texto de encabezados, pies de página y ruido innecesario."""
    #  Eliminar correos electrónicos
    texto = re.sub(r'\S+@\S+', '', texto)
    
    #  Eliminar patrones de números de página (ej: 1/67, 26/28)
    texto = re.sub(r'\b\d+/\d+\b', '', texto)
    
    #  Eliminar marcas de página del lector PDF (ej: --- PAGE 5 ---)
    texto = re.sub(r'--- PAGE \d+ ---', '', texto)
    
    # Eliminar nombres de profesores e instituciones 
    ruido_conocido = [
        "D. Molina y F.J. Rodríguez (CCIA)",
        "Francisco J. Rodríguez Díaz",
        "Javier Abad",
        "Universidad de Granada",
        "Fundamentos de Programación",
        "Departamento de Ciencias de la Computación e I.A.",
        "DECSAI",
        "Curso 2013/2014"
    ]
    for ruido in ruido_conocido:
        texto = texto.replace(ruido, "")
        
    # Eliminar palabras irrelevantes genéricas
    texto = re.sub(r'(?i)press any key.*?\n', '', texto) # (?i) ignora mayus/minus
    
    #  Limpiar saltos de línea múltiples y espacios en blanco excesivos
    texto = re.sub(r'\n{2,}', '\n', texto)
    texto = re.sub(r'\s{2,}', ' ', texto)
    
    return texto.strip()

def procesar_pdfs():
    print("Comprobando diapositivas existentes en la base de datos...")
    respuesta = supabase.table("apuntes").select("tema, diapositiva").eq("asignatura", "FP").execute()
    
    diapositivas_subidas = set((r["tema"], r["diapositiva"]) for r in respuesta.data)

    for archivo in os.listdir(CARPETA_PDFS):
        if not archivo.endswith(".pdf"):
            continue
            
        ruta = os.path.join(CARPETA_PDFS, archivo)
        print(f"\n Analizando: {archivo}...")
        
        with open(ruta, "rb") as f:
            lector = PyPDF2.PdfReader(f)
            
            for num_pagina, pagina in enumerate(lector.pages, start=1):
                if (archivo, num_pagina) in diapositivas_subidas:
                    continue
                    
                texto_bruto = pagina.extract_text()
                
                if not texto_bruto:
                    continue
                    
                texto_limpio = limpiar_texto(texto_bruto)
                
                # Descartamos si al limpiarlo se ha quedado casi vacío
                if len(texto_limpio) < 20:
                    print(f"   Diapositiva {num_pagina} descartada (sin contenido útil).")
                    continue
                
                exito = False
                while not exito:
                    try:
                        result = client_google.models.embed_content(
                            model="gemini-embedding-001",
                            contents=texto_limpio, 
                            config=types.EmbedContentConfig(
                                task_type="RETRIEVAL_DOCUMENT",
                                output_dimensionality=768
                            )
                        )
                        vector = result.embeddings[0].values
                        
                        data = {
                            "tema": archivo,
                            "contenido": texto_limpio, 
                            "embedding": vector,
                            "asignatura": "FP",
                            "diapositiva": num_pagina
                        }
                        supabase.table("apuntes").insert(data).execute()
                        print(f"   Diapositiva {num_pagina} subida.")
                        
                        exito = True
                        time.sleep(1.5) 
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                            print(f"   Límite de Google alcanzado. Pausando 45s...")
                            time.sleep(45)
                        else:
                            print(f"   Error desconocido en diapositiva {num_pagina}: {e}")
                            exito = True 

if __name__ == "__main__":
    procesar_pdfs()