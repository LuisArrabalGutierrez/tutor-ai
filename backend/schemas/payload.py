from pydantic import BaseModel
from typing import List, Dict

# Clase para representar cada mensaje del chat, con su rol (user, assistant, system) y su contenido
class MensajeChat(BaseModel):
    role: str
    content: str

# Clase para representar la petición de chat, que incluye una lista de mensajes y un diccionario de archivos (nombre -> contenido)
class ChatRequest(BaseModel):
    mensajes: List[MensajeChat]
   
    archivos: Dict[str, str] 


# Clase para representar la petición de ejecución, que solo incluye el diccionario de archivos (nombre -> contenido)
class ExecuteRequest(BaseModel):
    archivos: Dict[str, str]