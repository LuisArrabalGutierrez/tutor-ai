from pydantic import BaseModel
from typing import List

# Definimos la estructura exacta de un mensaje (quién habla y qué dice)
class MensajeChat(BaseModel):
    role: str
    content: str

# Actualizamos la petición para recibir la lista de objetos en vez de textos sueltos
class ChatRequest(BaseModel):
    mensajes: List[MensajeChat]
    codigo: str

class ExecuteRequest(BaseModel):
    code: str