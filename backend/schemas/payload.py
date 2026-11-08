from pydantic import BaseModel, field_validator
from typing import List, Dict, Optional

MAX_FILES = 200
MAX_PATH_CHARS = 255
MAX_EXECUTE_BYTES = 2 * 1024 * 1024
MAX_CHAT_PROJECT_BYTES = 10 * 1024 * 1024


def _validar_proyecto(archivos: Dict[str, str], max_bytes: int) -> Dict[str, str]:
    """Rutas relativas y sin `..` (se escriben en disco), y tamaño total acotado."""
    if len(archivos) > MAX_FILES:
        raise ValueError(f"Demasiados archivos (máximo {MAX_FILES}).")
    total = 0
    for ruta, contenido in archivos.items():
        partes = ruta.replace("\\", "/").split("/")
        if not ruta or len(ruta) > MAX_PATH_CHARS or "\0" in ruta or ruta.startswith("/") or ".." in partes:
            raise ValueError(f"Ruta de archivo no permitida: {ruta[:80]!r}")
        total += len(contenido)
    if total > max_bytes:
        raise ValueError(f"El proyecto supera el tamaño máximo ({max_bytes // (1024 * 1024)} MB).")
    return archivos


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

    @field_validator("archivos")
    @classmethod
    def _archivos_validos(cls, v):
        return _validar_proyecto(v, MAX_CHAT_PROJECT_BYTES) if v else v

# Petición para ejecutar código (si no usas WebSockets)
class ExecuteRequest(BaseModel):
    archivos: Dict[str, str]

    @field_validator("archivos")
    @classmethod
    def _archivos_validos(cls, v):
        return _validar_proyecto(v, MAX_EXECUTE_BYTES)
