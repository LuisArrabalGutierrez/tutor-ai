from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

CHAT_LIMIT = "15/minute"
EXECUTE_LIMIT = "30/minute"


def get_student_identifier(request: Request) -> str:
    """
    Identificador único por alumno para el Rate Limiter.
    Evita colapsar a todos los alumnos bajo la misma IP cuando se accede desde proxies (Vercel/Ngrok).
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        if len(token) > 15:
            return f"user:{token[-16:]}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        real_ip = forwarded_for.split(",")[0].strip()
        if real_ip:
            return f"ip:{real_ip}"

    return f"client:{get_remote_address(request)}"


# Instancia única compartida por todos los routers (main.py la registra en app.state)
limiter = Limiter(key_func=get_student_identifier)
