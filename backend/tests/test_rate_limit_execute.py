import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app
from services.rate_limit import EXECUTE_LIMIT
from routers import execute as execute_router


def test_execute_devuelve_429_al_superar_el_limite(monkeypatch):
    async def fake_compile(archivos):
        return {"output": "ok", "isError": False}

    monkeypatch.setattr(execute_router, "compile_and_run_project", fake_compile)
    maximo = int(EXECUTE_LIMIT.split("/")[0])
    payload = {"archivos": {"main.cpp": "int main(){}"}}
    headers = {"X-Forwarded-For": "203.0.113.77"}  # IP propia para no mezclar cuota con otros tests

    with TestClient(app) as client:
        estados = [client.post("/api/execute", json=payload, headers=headers).status_code for _ in range(maximo + 3)]

    assert estados[:maximo] == [200] * maximo
    assert 429 in estados[maximo:]
