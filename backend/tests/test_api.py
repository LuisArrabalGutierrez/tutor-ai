import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = pytest.mark.llm

CODIGO_CON_ERROR_LOGICO = {
    "main.cpp": '#include <iostream>\n#include "utils.h"\nusing namespace std;\n'
                'int main() { cout << "El doble de 5 es: " << calcularDoble(5) << endl; return 0; }',
    "utils.h": "#ifndef UTILS_H\n#define UTILS_H\nint calcularDoble(int n);\n#endif",
    "utils.cpp": '#include "utils.h"\nint calcularDoble(int n) { return n * 3; }',
}


def test_la_ia_localiza_el_error_logico_en_otro_archivo():
    """Memoria 5.5.1: el tutor lee todo el proyecto y orienta hacia utils.cpp sin dar la solución."""
    payload = {
        "historial": [{"role": "user", "content": "Intento calcular el doble de 5 pero el programa imprime 15 en lugar de 10. ¿Por qué falla mi lógica?"}],
        "archivos": CODIGO_CON_ERROR_LOGICO,
        "asignatura": "cpp",
        "terminal_context": "",
    }
    with TestClient(app) as client:
        response = client.post("/api/chat", json=payload, headers={"X-Forwarded-For": "203.0.113.90"})
    assert response.status_code == 200
    respuesta = response.json()["reply"].lower()
    assert any(pista in respuesta for pista in ["utils", "calculardoble", "función", "funcion"])
