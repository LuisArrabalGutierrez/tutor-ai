import os
import time
import asyncio
import json
import traceback
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async, get_socratic_response_stream_async

from auth.verify import get_optional_user, supabase
from services.analyst import update_student_profile

from slowapi import Limiter
from slowapi.util import get_remote_address

def get_student_identifier(request: Request) -> str:
    """
    Identificador único por alumno para el Rate Limiter.
    Evita colapsar a todos los alumnos bajo la misma IP cuando se accede desde proxies (Vercel/Ngrok).
    """
    # 1. Prioridad: Token de sesión del alumno autenticado
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        if len(token) > 15:
            return f"user:{token[-16:]}"

    # 2. Si no viene token, usar la IP real del alumno vía X-Forwarded-For
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        real_ip = forwarded_for.split(",")[0].strip()
        if real_ip:
            return f"ip:{real_ip}"

    # 3. Fallback a la IP de la conexión directa
    return f"client:{get_remote_address(request)}"

limiter = Limiter(key_func=get_student_identifier)
router = APIRouter()

# Caché en memoria para perfiles de estudiantes (evita consultas redundantes a Supabase)
_PROFILE_CACHE = {}
_PROFILE_TTL = 300 # 5 minutos

async def _fetch_user_profile(user_id: str) -> dict:
    """Carga el perfil pedagógico del alumno con caché en memoria (0ms tras la primera consulta)."""
    if not user_id or not supabase:
        return {}
    
    ahora = time.time()
    if user_id in _PROFILE_CACHE:
        perfil, expira = _PROFILE_CACHE[user_id]
        if ahora < expira:
            return perfil

    try:
        def _query():
            res = supabase.table("perfiles").select("*").eq("id", user_id).execute()
            return res.data[0] if res.data else {}
        perfil = await asyncio.to_thread(_query)
        if len(_PROFILE_CACHE) > 500:
            _PROFILE_CACHE.clear()
        _PROFILE_CACHE[user_id] = (perfil, ahora + _PROFILE_TTL)
        return perfil
    except Exception as e:
        print(f"⚠️ [Chat] Error cargando perfil: {e}")
        return {}

@router.post("/chat")
@limiter.limit("15/minute")
async def chat_endpoint(
    request: Request, 
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_optional_user)
):
    """Endpoint síncrono estándar (compatible con tests y clientes legacy)."""
    historial_dict = [m.model_dump() for m in body.historial]
    datos_perfil = await _fetch_user_profile(user_id) if user_id else {}

    try:
        respuesta = await get_socratic_response_async(
            historial=historial_dict,
            proyecto_archivos=body.archivos or {},
            terminal_context=body.terminal_context or "",
            asignatura=body.asignatura or "cpp",
            perfil_alumno=datos_perfil
        )

        # Análisis pedagógico en background con debounce (cada 3 interacciones o en la 2ª)
        if user_id and len(historial_dict) >= 2 and (len(historial_dict) % 3 == 0 or len(historial_dict) == 2):
            background_tasks.add_task(
                update_student_profile, 
                user_id, 
                historial_dict, 
                body.archivos,
                supabase
            )

        return {"reply": respuesta}
        
    except asyncio.CancelledError:
        print("🛑 [Chat] Petición cancelada por el alumno.")
        raise
        
    except Exception as e:
        traceback.print_exc()
        print(f"❌ Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en tutor: {str(e)}")


@router.post("/chat/stream")
@limiter.limit("15/minute")
async def chat_stream_endpoint(
    request: Request,
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_optional_user)
):
    """Endpoint de streaming en tiempo real (Server-Sent Events) para latencia percibida sub-200ms."""
    historial_dict = [m.model_dump() for m in body.historial]
    datos_perfil = await _fetch_user_profile(user_id) if user_id else {}

    # Análisis pedagógico en background con debounce (cada 3 interacciones o en la 2ª)
    if user_id and len(historial_dict) >= 2 and (len(historial_dict) % 3 == 0 or len(historial_dict) == 2):
        background_tasks.add_task(
            update_student_profile, 
            user_id, 
            historial_dict, 
            body.archivos,
            supabase
        )

    async def event_generator():
        try:
            async for token in get_socratic_response_stream_async(
                historial=historial_dict,
                proyecto_archivos=body.archivos or {},
                terminal_context=body.terminal_context or "",
                asignatura=body.asignatura or "cpp",
                perfil_alumno=datos_perfil
            ):
                if token:
                    # Emisión en formato SSE estándar (sin buffering en Vercel/Nginx)
                    yield f"data: {json.dumps({'token': token})}\n\n"
            
            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            print("🛑 [Stream] Flujo cancelado por el cliente.")
        except Exception as e:
            traceback.print_exc()
            print(f"❌ [Stream Error]: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
