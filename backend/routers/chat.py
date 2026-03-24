from fastapi import APIRouter
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async 

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    historial = [{"role": msg.role, "content": msg.content} for msg in request.mensajes]
    
    # MUY IMPORTANTE: Añadir 'await' aquí
    reply = await get_socratic_response_async(historial, request.archivos) 
    
    return {"respuesta": reply}