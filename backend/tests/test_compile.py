import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app

def test_compilar_codigo_valido():
    with TestClient(app) as client:
        payload = {"archivos": {"main.cpp": "#include <iostream>\nint main() { std::cout << \"Hola TFG\"; return 0; }"}}
        response = client.post("/api/execute", json=payload)
        assert response.status_code == 200
        assert "Hola TFG" in response.json()["output"]

def test_compilar_error_sintaxis():
    with TestClient(app) as client:
        payload = {"archivos": {"main.cpp": "int main() { return 0 }"}} # Error de sintaxis
        response = client.post("/api/execute", json=payload)
        assert response.json()["isError"] == True

def test_compilar_con_makefile():
    with TestClient(app) as client:
        payload = {
            "archivos": {
                "main.cpp": "#include <iostream>\nint main() { std::cout << \"Make OK\"; return 0; }",
                "Makefile": "all:\n\tg++ main.cpp -o main" 
            }
        }
        response = client.post("/api/execute", json=payload)
        assert "Make OK" in response.json()["output"]

def test_seguridad_bucle_infinito():
    with TestClient(app) as client:
        payload = {"archivos": {"main.cpp": "int main() { while(true) {} return 0; }"}}
        response = client.post("/api/execute", json=payload)
        # El sistema debería devolver un mensaje de tiempo excedido
        assert response.json()["isError"] == True

def test_seguridad_aislamiento_red():
    with TestClient(app) as client:
        payload = {"archivos": {"main.cpp": "#include <cstdlib>\nint main() { system(\"curl http://google.com\"); return 0; }"}}
        response = client.post("/api/execute", json=payload)
        # Como no hay red, la salida no debe contener HTML de Google
        assert "html" not in response.json()["output"].lower()