import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, execute, terminal, uploadPDF

# Importamos las dependencias de seguridad y pool
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from services.warm_pool import pool
from services.rate_limit import limiter
from tutor import start_tutor_runtime, stop_tutor_runtime
from contextlib import asynccontextmanager

# Lifespan para manejar el ciclo de vida del Warm Pool
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Esto se ejecuta al iniciar el servidor
    await pool.start_pool()
    # Servidor MCP con las herramientas del tutor (proceso hijo con su propio pool de contenedores).
    # Si se desactiva, se arranca de forma perezosa en el primer mensaje del chat.
    if os.getenv("TUTOR_MCP_EAGER", "1") != "0":
        await start_tutor_runtime()
    yield
    # Esto se ejecuta al cerrar el servidor (Ctrl+C)
    await stop_tutor_runtime()
    await pool.stop_pool()


app = FastAPI(title="Tutor IA Backend", lifespan=lifespan)

# Conectamos el limitador a la aplicación principal
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://tutor-ai-ugr.vercel.app"],    
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

#Incluimos las rutas
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(execute.router, prefix="/api", tags=["Compiler"])
app.include_router(terminal.router, tags=["Terminal"])
app.include_router(uploadPDF.router, tags=["PDF"])