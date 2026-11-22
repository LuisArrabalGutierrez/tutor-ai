"""Instancia de pruebas de la API para carga y DAST: mismo código, pool propio y LLM simulado.

- Pool `bench_api_*`: no toca los contenedores de producción.
- El tutor no arranca el servidor MCP (su pool usa el prefijo fijo `tutor_mcp_`) ni llama a Gemini o Groq:
  todas las respuestas del chat salen de un modelo falso con retardo fijo. Así la carga mide la API y
  no la cuota del proveedor.
Uso: python bench/carga/servidor_mock.py [--port 8100] [--primer-token-ms 100] [--token-ms 20]
"""
import argparse
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend(prefijo="bench_api_", tam=int(os.environ.get("BENCH_POOL", "3")))
os.environ["TUTOR_MCP_EAGER"] = "0"

RESPUESTA = "Hola, soy el tutor de pruebas. Cuéntame qué duda tienes y la vemos paso a paso. ¿Por dónde empezamos?"


class ModeloFalso:
    def __init__(self, primer_token_s: float, token_s: float):
        self.primer_token_s, self.token_s = primer_token_s, token_s

    async def astream(self, _mensajes):
        await asyncio.sleep(self.primer_token_s)
        for palabra in RESPUESTA.split(" "):
            yield SimpleNamespace(content=palabra + " ")
            await asyncio.sleep(self.token_s)

    async def ainvoke(self, _mensajes):
        await asyncio.sleep(self.primer_token_s + self.token_s * len(RESPUESTA.split(" ")))
        return SimpleNamespace(content=RESPUESTA)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--primer-token-ms", type=float, default=100)
    ap.add_argument("--token-ms", type=float, default=20)
    a = ap.parse_args()

    import tutor  # noqa: E402

    async def _sin_agentes():
        return None, None

    tutor.llm_fast = ModeloFalso(a.primer_token_ms / 1000, a.token_ms / 1000)
    tutor.llm_gemini = tutor.llm_groq = None
    tutor._get_agents = _sin_agentes

    import uvicorn  # noqa: E402
    from main import app  # noqa: E402

    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")
