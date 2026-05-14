import asyncio
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from schemas.payload import ChatRequest
from tutor import get_socratic_response_async 

from auth.verify import get_optional_user, supabase
from services.analyst import update_student_profile

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/chat")
@limiter.limit("5/minute")
async def chat_endpoint(
    request: Request, 
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_optional_user)
):
    # Verificamos si el token llega
    print(f"--- DEBUG CHAT ---")
    print(f"User ID detectado: {user_id}")
    
    historial_dict = [m.model_dump() for m in body.historial]
    datos_perfil = {}

    if user_id:
        try:
            resultado = supabase.table("perfiles").select("*").eq("id", user_id).execute()
            print(f"Datos perfil BD: {resultado.data}")
            if resultado.data:
                datos_perfil = resultado.data[0]
        except Exception as e:
            print(f"Error cargando perfil: {e}")

    try:
        respuesta = await get_socratic_response_async(
            historial=historial_dict,
            proyecto_archivos=body.archivos,
            terminal_context=body.terminal_context,
            asignatura=body.asignatura,
            perfil_alumno=datos_perfil
        )

        if user_id:
            print("Lanzando tarea en segundo plano...")
            background_tasks.add_task(
                update_student_profile, 
                user_id, 
                historial_dict, 
                body.archivos,
                supabase
            )
        else:
            print("No se lanza Analista porque user_id es None")

        return {"reply": respuesta}
        
    except asyncio.CancelledError:
        print("🛑 [Backend] Petición cancelada por el alumno. Deteniendo el agente IA...")
        raise
        
    except Exception as e:
        print(f"❌ Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del tutor")