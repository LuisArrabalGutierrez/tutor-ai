from fastapi import APIRouter
from schemas.payload import ChatRequest
from tutor import get_socratic_response 

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    reply = get_socratic_response(request.pregunta, request.codigo)    
    return {"respuesta": reply}