from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, execute

app = FastAPI(title="Tutor IA Backend")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectamos nuestras rutas limpias
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(execute.router, prefix="/api", tags=["Compiler"])