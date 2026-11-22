"""Paso 2.3: qué pasa con un bucle infinito.

2.3.1 tiempo total hasta la respuesta y exceso sobre el `timeout 30` interno.
2.3.2 el contenedor se recrea (cambia su ID) y no queda el proceso en la máquina.
Uso: python bench/sandbox/terminacion.py [--n 30]
"""
import argparse
import asyncio
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from services import compiler  # noqa: E402
from services.warm_pool import pool  # noqa: E402

BUCLE = {"main.cpp": "int main() { volatile unsigned long x = 0; while (true) { ++x; } return 0; }\n"}
VACIO = {"main.cpp": "int main() { return 0; }\n"}
TIMEOUT_INTERNO_S = 30


def ids() -> dict:
    r = subprocess.run(["docker", "ps", "--no-trunc", "--filter", "name=bench_warm_", "--format", "{{.Names}} {{.ID}}"],
                       capture_output=True, text=True)
    return dict(l.split() for l in r.stdout.splitlines() if l.strip())


def procesos_vivos() -> int:
    r = subprocess.run(["pgrep", "-fc", "programa.out"], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


async def _libre() -> None:
    while pool._recycling:
        await asyncio.gather(*list(pool._recycling.values()), return_exceptions=True)


async def main(n: int) -> None:
    out = c.Csv("sandbox_terminacion",
                ["caso", "rep", "total_ms", "salida_ok", "contenedor_recreado", "procesos_restantes"],
                {"timeout_interno_s": TIMEOUT_INTERNO_S})
    await pool.start_pool()
    try:
        # Referencia: mismo camino con un programa que termina al instante (compilación + copias)
        for rep in range(10):
            with c.Crono() as t:
                await compiler.compile_and_run_project(VACIO)
            await _libre()
            out.fila(caso="referencia", rep=rep, total_ms=round(t.ms, 2), salida_ok=1,
                     contenedor_recreado="", procesos_restantes="")
        for rep in range(n):
            antes = ids()
            with c.Crono() as t:
                res = await compiler.compile_and_run_project(BUCLE)
            await _libre()
            despues = ids()
            recreados = sum(1 for k in antes if despues.get(k) != antes[k])
            out.fila(caso="bucle", rep=rep, total_ms=round(t.ms, 2),
                     salida_ok=int(res["isError"] and "tiempo máximo" in res["output"]),
                     contenedor_recreado=int(recreados >= 1), procesos_restantes=procesos_vivos())
    finally:
        await pool.stop_pool()
        out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    asyncio.run(main(ap.parse_args().n))
