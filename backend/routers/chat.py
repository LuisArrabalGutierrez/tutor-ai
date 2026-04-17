from fastapi import APIRouter
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async 

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Convertimos los objetos Pydantic a diccionarios simples para tutor.py
    historial_dict = [m.model_dump() for m in request.historial]
    
    respuesta = await get_socratic_response_async(
        historial=historial_dict,
        proyecto_archivos=request.archivos,
        terminal_context=request.terminal_context,
        asignatura=request.asignatura
    )
    return {"reply": respuesta}