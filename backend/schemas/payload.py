from pydantic import BaseModel
from typing import List, Dict, Optional

# Representa un mensaje individual del chat
class MensajeChat(BaseModel):
    role: str # 'user', 'assistant' o 'system'
    content: str

# Petición principal del chat
class ChatRequest(BaseModel):
    historial: List[MensajeChat] # Lista de mensajes para mantener el contexto
    archivos: Optional[Dict[str, str]] = {}
    terminal_context: Optional[str] = "" 
    asignatura: Optional[str] = "cpp" # 'cpp' o 'linux'

# Petición para ejecutar código (si no usas WebSockets)
class ExecuteRequest(BaseModel):
    archivos: Dict[str, str]