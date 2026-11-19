"""Pasos 2.1.1 a 2.1.3: arranque en frío, Warm Pool y coste del reciclado.

Uso: python bench/sandbox/arranque.py [frio|pool|rafagas|todo] [--n 30]
"""
import argparse
import asyncio
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from services.warm_pool import WarmPoolManager  # noqa: E402

CALENTAMIENTO = 3


def _docker(*args: str) -> None:
    subprocess.run(["docker", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def frio(n: int) -> None:
    """`docker run -d` con las banderas del pool y después `docker exec true`: lo que tardaría
    una compilación en poder empezar si no hubiera contenedores precalentados."""
    out = c.Csv("sandbox_frio", ["rep", "calentamiento", "run_ms", "exec_ms", "total_ms"],
                {"descartadas_calentamiento": CALENTAMIENTO})
    nombre = "bench_frio"
    for rep in range(n + CALENTAMIENTO):
        _docker("rm", "-f", nombre)
        with c.Crono() as t_run:
            subprocess.run(["docker", "run", "-d", "--rm", "--name", nombre, *c.BANDERAS_POOL,
                            *c.banderas_seguridad(), c.IMAGEN, "sleep", "infinity"],
                           stdout=subprocess.DEVNULL, check=True)
        with c.Crono() as t_exec:
            subprocess.run(["docker", "exec", nombre, "true"], check=True)
        out.fila(rep=rep, calentamiento=int(rep < CALENTAMIENTO), run_ms=round(t_run.ms, 2),
                 exec_ms=round(t_exec.ms, 2), total_ms=round(t_run.ms + t_exec.ms, 2))
    _docker("rm", "-f", nombre)
    out.cerrar()


async def _exec_true(nombre: str) -> None:
    p = await asyncio.create_subprocess_exec("docker", "exec", nombre, "true")
    await p.wait()


async def _esperar_reciclado(pool: WarmPoolManager) -> None:
    while pool._recycling:
        await asyncio.gather(*list(pool._recycling.values()), return_exceptions=True)


async def con_pool(n: int) -> None:
    """Pool libre: get_container() + `docker exec true`, y lo que tarda release() en dejar otro listo."""
    out = c.Csv("sandbox_pool", ["rep", "calentamiento", "get_ms", "exec_ms", "total_ms", "reciclado_ms"],
                {"descartadas_calentamiento": CALENTAMIENTO, "pool_size": 3})
    pool = WarmPoolManager(pool_size=3, prefix="bench_warm_")
    await pool.start_pool()
    try:
        for rep in range(n + CALENTAMIENTO):
            with c.Crono() as t_get:
                nombre = await pool.get_container()
            with c.Crono() as t_exec:
                await _exec_true(nombre)
            with c.Crono() as t_rec:
                pool.release(nombre)
                await _esperar_reciclado(pool)
            out.fila(rep=rep, calentamiento=int(rep < CALENTAMIENTO), get_ms=round(t_get.ms, 2),
                     exec_ms=round(t_exec.ms, 2), total_ms=round(t_get.ms + t_exec.ms, 2),
                     reciclado_ms=round(t_rec.ms, 2))
    finally:
        await pool.stop_pool()
        out.cerrar()


async def rafagas(reps: int) -> None:
    """Llegan k peticiones a la vez a un pool de 3. Cada una espera contenedor, lo usa y lo suelta."""
    out = c.Csv("sandbox_rafagas", ["rafaga", "rep", "peticion", "espera_ms", "total_ms"], {"pool_size": 3})
    pool = WarmPoolManager(pool_size=3, prefix="bench_warm_")
    await pool.start_pool()

    async def peticion(k: int, rep: int, i: int) -> None:
        with c.Crono() as t_total:
            with c.Crono() as t_get:
                nombre = await pool.get_container(timeout=120)
            await _exec_true(nombre)
            pool.release(nombre)
        out.fila(rafaga=k, rep=rep, peticion=i, espera_ms=round(t_get.ms, 2), total_ms=round(t_total.ms, 2))

    try:
        for k in (3, 6, 10):
            for rep in range(reps):
                await asyncio.gather(*(peticion(k, rep, i) for i in range(k)))
                await _esperar_reciclado(pool)
    finally:
        await pool.stop_pool()
        out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("que", nargs="?", default="todo", choices=["frio", "pool", "rafagas", "todo"])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--reps-rafaga", type=int, default=10)
    a = ap.parse_args()
    if a.que in ("frio", "todo"):
        frio(a.n)
    if a.que in ("pool", "todo"):
        asyncio.run(con_pool(a.n))
    if a.que in ("rafagas", "todo"):
        asyncio.run(rafagas(a.reps_rafaga))
