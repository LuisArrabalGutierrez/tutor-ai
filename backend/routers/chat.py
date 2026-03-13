from fastapi import APIRouter
from schemas.payload import ChatRequest
from tutor import get_socratic_response 

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    historial = [{"role": msg.role, "content": msg.content} for msg in request.mensajes]
    reply = get_socratic_response(historial, request.codigo)
    return {"respuesta": reply}