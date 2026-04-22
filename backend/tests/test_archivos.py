import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_pdf_endpoint_sin_cabecera():
    archivo_falso = ("test.pdf", b"%PDF-1.4 archivo vacio", "application/pdf")
    response = client.post("/upload-pdf", files={"file": archivo_falso})
    assert response.status_code == 422 # Falla porque falta el Header de sesión

def test_upload_pdf_vacio_o_invalido():
    archivo_falso = ("test.pdf", b"%PDF-1.4 sin texto real", "application/pdf")
    response = client.post( "/upload-pdf",  files={"file": archivo_falso}, headers={"x-session-id": "test_session_123"})
    data = response.json()
    assert "vacío" in data.get("mensaje", "").lower() or "error" in data

# --- TEST DE SEGURIDAD RAM ---

def test_seguridad_limite_tamano_pdf():
    # Simulamos un "PDF Bomba" de 11 MB creado virtualmente en la memoria
    archivo_pesado_bytes = b"0" * (11 * 1024 * 1024) 
    archivo_pesado = ("pesado.pdf", archivo_pesado_bytes, "application/pdf")
    
    response = client.post(
        "/upload-pdf", 
        files={"file": archivo_pesado}, 
        headers={"x-session-id": "test_session_123"}
    )
    
    # El servidor debe rechazarlo inmediatamente con un código 413 (Payload Too Large)
    assert response.status_code == 413
    assert "demasiado grande" in response.json()["error"].lower()