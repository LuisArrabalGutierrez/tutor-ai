import asyncio
import json
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async, get_socratic_response_stream_async

from auth.verify import get_optional_user, supabase
from services.analyst import update_student_profile

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

async def _fetch_user_profile(user_id: str) -> dict:
    """Carga el perfil pedagógico del alumno en un hilo sin bloquear el Event Loop."""
    if not user_id or not supabase:
        return {}
    try:
        def _query():
            res = supabase.table("perfiles").select("*").eq("id", user_id).execute()
            return res.data[0] if res.data else {}
        return await asyncio.to_thread(_query)
    except Exception as e:
        print(f"⚠️ [Chat] Error cargando perfil: {e}")
        return {}

@router.post("/chat")
@limiter.limit("5/minute")
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

        if user_id:
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
        print(f"❌ Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del tutor")


@router.post("/chat/stream")
@limiter.limit("5/minute")
async def chat_stream_endpoint(
    request: Request,
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_optional_user)
):
    """Endpoint de streaming en tiempo real (Server-Sent Events) para latencia percibida sub-300ms."""
    historial_dict = [m.model_dump() for m in body.historial]
    datos_perfil = await _fetch_user_profile(user_id) if user_id else {}

    if user_id:
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
                    # Formato SSE estándar
                    yield f"data: {json.dumps({'token': token})}\n\n"
            
            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            print("🛑 [Stream] Flujo cancelado por el cliente.")
        except Exception as e:
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
