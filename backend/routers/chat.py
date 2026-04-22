from fastapi import APIRouter, Request, HTTPException
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async 

from slowapi import Limiter
from slowapi.util import get_remote_address

# Configuramos el limitador por IP
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/chat")
@limiter.limit("5/minute") # [SEGURIDAD] Máximo 5 peticiones por minuto por alumno
async def chat_endpoint(request: Request, body: ChatRequest):
    # 'request' es obligatorio para que slowapi pueda leer la IP
    historial_dict = [m.model_dump() for m in body.historial]
    
    respuesta = await get_socratic_response_async(
        historial=historial_dict,
        proyecto_archivos=body.archivos,
        terminal_context=body.terminal_context,
        asignatura=body.asignatura
    )
    return {"reply": respuesta}