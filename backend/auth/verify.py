import os
import asyncio
from fastapi import Header
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

async def get_optional_user(authorization: str = Header(None)):
    if not authorization or not supabase:
        return None

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None

    try:
        # Ejecutamos la verificación síncrona en un hilo separado para no bloquear el Event Loop
        user_res = await asyncio.to_thread(supabase.auth.get_user, token)
        if user_res and user_res.user:
            return user_res.user.id
        return None
    except Exception:
        return None
