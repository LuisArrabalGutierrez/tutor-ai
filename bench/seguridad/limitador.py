"""F-5: evasión del limitador cambiando la identidad que declara el cliente.

El limitador (services/rate_limit.py) identifica al alumno por los últimos 16 caracteres de cualquier `Bearer`
o por la primera IP de `X-Forwarded-For`, sin comprobar ninguna de las dos. Se mandan 60 peticiones seguidas a
/api/execute (límite 30/min) con cuatro estrategias y se cuentan las aceptadas. La compilación se sustituye por
una respuesta fija: lo que se mide es el limitador, no el sandbox.

Uso: python bench/seguridad/limitador.py [--reps 3]
"""
import argparse
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend("bench_lim_", 1)
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from routers import execute as execute_router  # noqa: E402
from services.rate_limit import EXECUTE_LIMIT  # noqa: E402

N = 60
CUERPO = {"archivos": {"main.cpp": "int main() { return 0; }\n"}}


async def _compilar_falso(archivos):
    return {"output": "ok", "isError": False}


def cabeceras(estrategia: str, rep: int, i: int) -> dict:
    if estrategia == "misma_ip":
        return {"X-Forwarded-For": f"198.51.100.{rep + 1}"}
    if estrategia == "xff_rotada":
        return {"X-Forwarded-For": f"10.{rep}.{i // 250}.{i % 250}"}
    if estrategia == "bearer_falso":
        return {"Authorization": "Bearer " + secrets.token_hex(12)}
    return {}  # sin_cabeceras: cuenta la dirección de la conexión


def main(a) -> None:
    execute_router.compile_and_run_project = _compilar_falso
    esperadas = int(EXECUTE_LIMIT.split("/")[0])
    out = c.Csv("seguridad_limitador", ["estrategia", "rep", "enviadas", "aceptadas", "rechazadas_429", "otras",
                                        "esperadas"], {"limite": EXECUTE_LIMIT, "endpoint": "/api/execute"})
    cliente = TestClient(app)  # sin `with`: no arranca el Warm Pool
    for rep in range(a.reps):
        for estrategia in ("misma_ip", "sin_cabeceras", "xff_rotada", "bearer_falso"):
            if estrategia == "sin_cabeceras":
                app.state.limiter.reset()  # la dirección de TestClient es siempre la misma
            codigos = [cliente.post("/api/execute", json=CUERPO, headers=cabeceras(estrategia, rep, i)).status_code
                       for i in range(N)]
            out.fila(estrategia=estrategia, rep=rep, enviadas=N, aceptadas=codigos.count(200),
                     rechazadas_429=codigos.count(429), otras=N - codigos.count(200) - codigos.count(429),
                     esperadas=esperadas)
            print(estrategia, rep, codigos.count(200), codigos.count(429), flush=True)
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    main(ap.parse_args())
