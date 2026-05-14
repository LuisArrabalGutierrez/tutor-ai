from fastapi import Header
from supabase import create_client
import os

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

async def get_optional_user(authorization: str = Header(None)):
    if not authorization: return None

    #extraemos el token JWT del header "Authorization"
    token = authorization.replace("Bearer ", "")
    try:
        # Verificamos el token y obtenemos el usuario asociado
        user = supabase.auth.get_user(token)
        return user.user.id
    except: return None