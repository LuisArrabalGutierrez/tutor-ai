import os
import time
import asyncio
from fastapi import Header
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

# Caché en memoria para tokens JWT (evita una llamada HTTP a Supabase Auth en cada mensaje)
_TOKEN_CACHE = {}
_TOKEN_TTL = 300 # 5 minutos de validez en caché

async def get_optional_user(authorization: str = Header(None)):
    if not authorization or not supabase:
        return None

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None

    ahora = time.time()
    # 1. Comprobación instantánea en memoria (0ms)
    if token in _TOKEN_CACHE:
        user_id, expira = _TOKEN_CACHE[token]
        if ahora < expira:
            return user_id

    # 2. Si no está en caché, validación en hilo separado
    try:
        user_res = await asyncio.to_thread(supabase.auth.get_user, token)
        if user_res and user_res.user:
            uid = user_res.user.id
            # Guardamos en caché
            if len(_TOKEN_CACHE) > 500:
                _TOKEN_CACHE.clear()
            _TOKEN_CACHE[token] = (uid, ahora + _TOKEN_TTL)
            return uid
        return None
    except Exception:
        return None
