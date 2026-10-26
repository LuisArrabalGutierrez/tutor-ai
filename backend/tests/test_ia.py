import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_chat_saludo_basico():
    payload = {
        "historial": [{"role": "user", "content": "Hola"}],
        "archivos": {}, "asignatura": "cpp", "terminal_context": ""
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    assert len(response.json()["reply"]) > 0

def test_chat_contexto_linux():
    payload = {
        "historial": [{"role": "user", "content": "Dime un comando para listar archivos"}],
        "archivos": {}, "asignatura": "linux", "terminal_context": "usuario@linux:~/TFG$"
    }
    response = client.post("/api/chat", json=payload)
    respuesta = response.json()["reply"].lower()
    assert "ls" in respuesta or "comando" in respuesta

def test_chat_streaming_endpoint():
    payload = {
        "historial": [{"role": "user", "content": "Hola"}],
        "archivos": {}, "asignatura": "cpp", "terminal_context": ""
    }
    response = client.post("/api/chat/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

# --- TEST DE SEGURIDAD ANTI-SPAM ---

def test_seguridad_rate_limiting_chat():
    payload_valido = {
        "historial": [{"role": "user", "content": "Spam test"}], 
        "archivos": {}, 
        "asignatura": "cpp", 
        "terminal_context": ""
    }
    
    # Consumimos las 5 peticiones permitidas por minuto
    for _ in range(5):
        client.post("/api/chat", json=payload_valido)
        
    # La petición 6 DEBE devolver un error 429 (Too Many Requests)
    response_bloqueada = client.post("/api/chat", json=payload_valido)
    assert response_bloqueada.status_code == 429
