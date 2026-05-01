import asyncio # <-- Añadimos esta importación
from fastapi import APIRouter, Request, HTTPException
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async 

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/chat")
@limiter.limit("5/minute")
async def chat_endpoint(request: Request, body: ChatRequest):
    historial_dict = [m.model_dump() for m in body.historial]
    
    try:
        # Lanzamos la ejecución asíncrona de LangGraph
        respuesta = await get_socratic_response_async(
            historial=historial_dict,
            proyecto_archivos=body.archivos,
            terminal_context=body.terminal_context,
            asignatura=body.asignatura
        )
        return {"reply": respuesta}
        
    except asyncio.CancelledError:
        # [SEGURIDAD/AHORRO] Si el alumno pulsa "Detener" en React o cierra la pestaña
        print("🛑 [Backend] Petición cancelada por el alumno. Deteniendo el agente IA...")
        
        # Al hacer raise de nuevo, FastAPI limpia los recursos y detiene las llamadas 
        # asíncronas internas (como el ainvoke del agente) cortando el gasto en Groq.
        raise
        
    except Exception as e:
        # Manejo de cualquier otro error del servidor
        print(f"❌ Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del tutor")