from pydantic import BaseModel


# Aquí definimos los modelos de datos que esperamos recibir en las peticiones POST
# desde el front, es como las interfaces en typescript. 

class ChatRequest(BaseModel):
    pregunta: str
    codigo: str

class ExecuteRequest(BaseModel):
    code: str