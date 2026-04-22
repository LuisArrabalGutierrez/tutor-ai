import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_compilar_codigo_valido():
    payload = {"archivos": {"main.cpp": "#include <iostream>\nint main() { std::cout << \"Hola TFG\"; return 0; }"}}
    response = client.post("/api/execute", json=payload)
    assert response.status_code == 200
    assert "Hola TFG" in response.json()["output"]

def test_compilar_error_sintaxis():
    payload = {"archivos": {"main.cpp": "int main() { return 0 }"}} # Falta punto y coma
    response = client.post("/api/execute", json=payload)
    assert response.json()["isError"] == True

def test_compilar_con_makefile():
    payload = {
        "archivos": {
            "main.cpp": "#include <iostream>\nint main() { std::cout << \"Make OK\"; return 0; }",

            "Makefile": "all:\n\tg++ main.cpp -o main" 
        }
    }
    response = client.post("/api/execute", json=payload)
    assert response.status_code == 200
    assert "Make OK" in response.json()["output"]

def test_compilar_multiples_archivos_headers():
    payload = {
        "archivos": {
            "main.cpp": "#include <iostream>\n#include \"calculo.h\"\nint main() { std::cout << sumar(10, 5); return 0; }",
            "calculo.h": "int sumar(int a, int b);",
            "calculo.cpp": "#include \"calculo.h\"\nint sumar(int a, int b) { return a + b; }"
        }
    }
    response = client.post("/api/execute", json=payload)
    assert "15" in response.json()["output"]

# --- TESTS DE SEGURIDAD DOCKER ---

def test_seguridad_bucle_infinito():
    # Verifica que Docker corta la ejecución si hay un while(true)
    payload = {"archivos": {"main.cpp": "int main() { while(true) {} return 0; }"}}
    response = client.post("/api/execute", json=payload)
    assert "tiempo excedido" in response.json()["output"].lower() or "timeout" in response.json()["output"].lower()

def test_seguridad_aislamiento_red():
    # [NUEVO] Verifica que el contenedor no tiene internet (--network none)
    # Intentamos hacer un ping o descargar algo con un comando de sistema en C++
    payload = {"archivos": {"main.cpp": "#include <cstdlib>\nint main() { system(\"wget -qO- http://google.com\"); return 0; }"}}
    response = client.post("/api/execute", json=payload)
    data = response.json()
    # Si tuviera internet, descargaría el HTML de Google. Como está aislado, no debe haber HTML.
    assert "html" not in data["output"].lower()