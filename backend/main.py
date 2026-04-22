from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, execute, terminal,uploadPDF

# Importamos las dependencias de seguridad
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app = FastAPI(title="Tutor IA Backend")

# Conectamos el limitador a la aplicación principal
app.state.limiter = chat.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(execute.router, prefix="/api", tags=["Compiler"])
app.include_router(terminal.router, tags=["Terminal"])
app.include_router(uploadPDF.router, tags=["PDF"])