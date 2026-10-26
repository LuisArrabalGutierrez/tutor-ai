import os
import io
import asyncio
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
        print("⚠️ ADVERTENCIA: No se encontró GOOGLE_API_KEY en el entorno.")
    client_google = genai.Client(api_key=api_key) if api_key else None
except Exception as e:
    print(f"❌ Error al inicializar Google Client: {e}")
    client_google = None

# Límite máximo de sesiones en memoria RAM para evitar fugas (OOM)
MAX_SESSIONS_IN_MEMORY = 50

@router.post("/upload-pdf")
async def upload_personal_pdf(
    file: UploadFile = File(...),
    x_session_id: str = Header(...)
):
    try:
        # 1. Validar tamaño (10 MB máximo)
        MAX_MB = 10
        if file.size and file.size > (MAX_MB * 1024 * 1024):
            return JSONResponse(
                status_code=413, 
                content={"error": f"El archivo es demasiado grande. Tamaño máximo permitido: {MAX_MB}MB."}
            )

        # 2. Control de memoria RAM (evicción LRU de sesiones antiguas)
        if len(memoria_usuarios) >= MAX_SESSIONS_IN_MEMORY:
            primer_id = next(iter(memoria_usuarios))
            memoria_usuarios.pop(primer_id, None)

        memoria_usuarios[x_session_id] = []
        
        pdf_bytes = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        
        texto_completo = ""
        for page in pdf_reader.pages:
            texto_page = page.extract_text()
            if texto_page:
                texto_completo += texto_page + "\n"
            
        bloques = [b.strip() for b in texto_completo.split('\n\n') if len(b.strip()) > 100]
        
        if not bloques:
            return JSONResponse(content={"mensaje": "El PDF está vacío o es una imagen escaneada."})

        if not client_google:
            return JSONResponse(status_code=500, content={"error": "Servicio de Google GenAI no configurado."})

        bloques_procesados = 0
        # Limitamos a un máximo de 25 bloques por PDF de sesión para no agotar cuota
        bloques_a_procesar = bloques[:25]

        for bloque in bloques_a_procesar:
            try:
                def _embed():
                    return client_google.models.embed_content(
                        model="gemini-embedding-001",
                        contents=bloque,
                        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768)
                    )
                
                result = await asyncio.to_thread(_embed)
                
                memoria_usuarios[x_session_id].append({
                    "texto": bloque,
                    "vector": np.array(result.embeddings[0].values)
                })
                bloques_procesados += 1
                
                # Pausa asíncrona no bloqueante
                await asyncio.sleep(0.1)
                
            except Exception as e_chunk:
                print(f"⚠️ Salto de bloque por límite de API: {e_chunk}")
                continue
            
        return JSONResponse(content={"mensaje": f"PDF procesado correctamente. {bloques_procesados} bloques indexados en la sesión."})
        
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Error interno del servidor al procesar el PDF."})
