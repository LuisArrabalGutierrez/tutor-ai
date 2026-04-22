import os
import io
import time
import numpy as np
import PyPDF2
import traceback
from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv

from schemas.state import memoria_usuarios

load_dotenv()

router = APIRouter()

try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(" ADVERTENCIA: No se encontró GOOGLE_API_KEY en el entorno.")
    client_google = genai.Client(api_key=api_key)
except Exception as e:
    print(f" Error al inicializar Google Client: {e}")

@router.post("/upload-pdf")
async def upload_personal_pdf(
    file: UploadFile = File(...),
    x_session_id: str = Header(...)
):
    try:
        # Validar el tamaño del archivo (Límite: 10 MB)
        # Esto evita que un alumno suba un archivo de 2GB y colapse la RAM del servidor.
        MAX_MB = 10
        if file.size and file.size > (MAX_MB * 1024 * 1024):
            print(f" [BLOQUEO] Intento de subida de PDF masivo rechazado. Sesión: {x_session_id}")
            return JSONResponse(
                status_code=413, 
                content={"error": f"El archivo es demasiado grande. Tamaño máximo permitido: {MAX_MB}MB."}
            )

        print(f" Recibiendo PDF '{file.filename}' para sesión: {x_session_id}")
        
        # Limpiamos la memoria antigua de este usuario
        memoria_usuarios[x_session_id] = []
        
        # [SEGURIDAD] 2. Lectura controlada del archivo en RAM (solo si pasó el filtro de tamaño)
        pdf_bytes = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        
        texto_completo = ""
        for page in pdf_reader.pages:
            texto_page = page.extract_text()
            if texto_page:
                texto_completo += texto_page + "\n"
            
        # Troceamos por párrafos (Chunks)
        bloques = [b.strip() for b in texto_completo.split('\n\n') if len(b.strip()) > 100]
        
        if not bloques:
            print(" El PDF está vacío o es una imagen escaneada (sin texto OCR).")
            return JSONResponse(content={"mensaje": "El PDF está vacío o es una imagen escaneada."})

        print(f" Enviando {len(bloques)} bloques a Google paso a paso para no saturar la API...")
        
        bloques_procesados = 0
        for bloque in bloques:
            try:
                # Vectorizamos de UNO EN UNO
                result = client_google.models.embed_content(
                    model="gemini-embedding-001",
                    contents=bloque,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768)
                )
                
                # Guardamos este bloque en concreto
                memoria_usuarios[x_session_id].append({
                    "texto": bloque,
                    "vector": np.array(result.embeddings[0].values)
                })
                bloques_procesados += 1
                
                # Le damos un respiro de medio segundo a Google para evitar el Error 429 (Rate Limit)
                time.sleep(0.5) 
                
            except Exception as e_chunk:
                print(f" Se saltó un bloque por límite de cuota de Google. Continuando... Error: {e_chunk}")
                continue # Si falla uno, saltamos al siguiente en lugar de tirar el servidor
            
        print(f" ¡Éxito! {bloques_procesados} bloques guardados en la memoria RAM del usuario.")
        return JSONResponse(content={"mensaje": f"PDF procesado correctamente. {bloques_procesados} bloques indexados en la sesión."})
        
    except Exception as e:
        print("\n CRASH INTERNO EN EL SERVIDOR (Detalles abajo):")
        traceback.print_exc() # Esto imprimirá el error real en tu consola negra
        return JSONResponse(status_code=500, content={"error": "Error interno del servidor al procesar el PDF."})