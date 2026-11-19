"""Paso 2.5.5: precisión del limitador. Se inyecta un patrón conocido y se cuentan las aceptadas.

Patrones: `uniforme` (60 peticiones repartidas en 60 s) y `rafaga` (60 seguidas).
Esperadas por ventana de un minuto: 15 en el chat y 30 en /api/execute.
Uso: python bench/carga/rate_limit.py --url http://127.0.0.1:8100 [--reps 3]
"""
import argparse
import asyncio
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

CHAT = {"historial": [{"role": "user", "content": "hola"}], "archivos": {}, "asignatura": "cpp"}
EXEC = {"archivos": {"main.cpp": "int main() { return 0; }\n"}}
CASOS = [("chat", "/api/chat/stream", CHAT, 15), ("execute", "/api/execute", EXEC, 30)]
N = 60


async def una(http, url, ruta, cuerpo, ident) -> int:
    try:
        r = await http.post(url + ruta, json=cuerpo, headers={"X-Forwarded-For": ident})
        return r.status_code
    except Exception:
        return 0


async def main(a) -> None:
    out = c.Csv("carga_rate_limit", ["endpoint", "patron", "rep", "enviadas", "aceptadas", "rechazadas_429", "otras",
                                     "esperadas", "duracion_s"], {"peticiones_por_prueba": N})
    async with httpx.AsyncClient(timeout=90) as http:
        for nombre, ruta, cuerpo, esperadas in CASOS:
            for patron in ("uniforme", "rafaga"):
                for rep in range(a.reps):
                    ident = f"10.6.{hash((nombre, patron)) % 200}.{rep + 1}"
                    t0 = time.monotonic()
                    tareas = []
                    for i in range(N):
                        tareas.append(asyncio.create_task(una(http, a.url, ruta, cuerpo, ident)))
                        if patron == "uniforme":
                            await asyncio.sleep(max(0.0, t0 + (i + 1) * 60 / N - time.monotonic()))
                    codigos = await asyncio.gather(*tareas)
                    out.fila(endpoint=nombre, patron=patron, rep=rep, enviadas=N, aceptadas=codigos.count(200),
                             rechazadas_429=codigos.count(429), otras=N - codigos.count(200) - codigos.count(429),
                             esperadas=esperadas, duracion_s=round(time.monotonic() - t0, 1))
                    print(nombre, patron, rep, codigos.count(200), codigos.count(429), flush=True)
                    await asyncio.sleep(61)  # ventana nueva para la siguiente prueba
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8100")
    ap.add_argument("--reps", type=int, default=3)
    asyncio.run(main(ap.parse_args()))
