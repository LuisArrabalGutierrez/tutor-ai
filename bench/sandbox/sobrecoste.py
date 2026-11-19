"""Paso 2.2: sobrecoste de compilar y ejecutar en el sandbox frente a una línea base.

Línea base `host`: g++ y el binario directamente en la máquina.
Línea base `contenedor`: la misma imagen sin límites de CPU ni memoria (para máquinas sin g++).
Uso: python bench/sandbox/sobrecoste.py [--n 30] [--base host|contenedor]
"""
import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from services import compiler  # noqa: E402
from services.warm_pool import pool  # noqa: E402

PROGRAMAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "programas")
CALENTAMIENTO = 2


def cargar(nombre: str) -> dict:
    base = os.path.join(PROGRAMAS, nombre)
    archivos = {}
    for raiz, _, ficheros in os.walk(base):
        for f in ficheros:
            ruta = os.path.join(raiz, f)
            with open(ruta, encoding="utf-8") as fh:
                archivos[os.path.relpath(ruta, base)] = fh.read()
    return archivos


def _volcar(archivos: dict, destino: str) -> str:
    usa_makefile = compiler._write_project(destino, archivos)
    return compiler._build_script(archivos, usa_makefile)


def en_host(archivos: dict) -> float:
    with tempfile.TemporaryDirectory() as d:
        script = _volcar(archivos, d)
        with c.Crono() as t:
            r = subprocess.run(["bash", "-c", script], cwd=d, capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode()[:300])
    return t.ms


def en_contenedor_sin_limites(archivos: dict) -> float:
    """Contenedor ya arrancado, sin límites: aísla el coste de los límites y del copiado."""
    nombre = "bench_base"
    with tempfile.TemporaryDirectory(dir=compiler.LOCAL_TEMP_DIR) as d:
        script = _volcar(archivos, d)
        subprocess.run(["docker", "exec", nombre, "rm", "-rf", "/tmp/w"], check=False)
        with c.Crono() as t:
            subprocess.run(["docker", "exec", nombre, "mkdir", "-p", "/tmp/w"], check=True)
            subprocess.run(["docker", "cp", f"{d}/.", f"{nombre}:/tmp/w/"], check=True, stdout=subprocess.DEVNULL)
            r = subprocess.run(["docker", "exec", "-w", "/tmp/w", nombre, "bash", "-c", script], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode()[:300])
    return t.ms


async def en_sandbox(archivos: dict) -> float:
    with c.Crono() as t:
        res = await compiler.compile_and_run_project(archivos)
    if res["isError"]:
        raise RuntimeError(res["output"][:300])
    while pool._recycling:  # pool libre antes de la siguiente repetición
        await asyncio.gather(*list(pool._recycling.values()), return_exceptions=True)
    return t.ms


async def main(n: int, base: str) -> None:
    out = c.Csv("sandbox_sobrecoste", ["programa", "via", "rep", "calentamiento", "ms"],
                {"descartadas_calentamiento": CALENTAMIENTO, "linea_base": base})
    if base == "contenedor":
        subprocess.run(["docker", "rm", "-f", "bench_base"], capture_output=True)
        subprocess.run(["docker", "run", "-d", "--rm", "--name", "bench_base", "--network", "none",
                        c.IMAGEN, "sleep", "infinity"], check=True, stdout=subprocess.DEVNULL)
    await pool.start_pool()
    try:
        for prog in ("hola", "mediano", "makefile", "calculo"):
            archivos = cargar(prog)
            for rep in range(n + CALENTAMIENTO):
                ms_base = en_host(archivos) if base == "host" else en_contenedor_sin_limites(archivos)
                out.fila(programa=prog, via=base, rep=rep, calentamiento=int(rep < CALENTAMIENTO), ms=round(ms_base, 2))
                ms_sb = await en_sandbox(archivos)
                out.fila(programa=prog, via="sandbox", rep=rep, calentamiento=int(rep < CALENTAMIENTO), ms=round(ms_sb, 2))
    finally:
        await pool.stop_pool()
        if base == "contenedor":
            subprocess.run(["docker", "rm", "-f", "bench_base"], capture_output=True)
        out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--base", default="host" if shutil.which("g++") else "contenedor", choices=["host", "contenedor"])
    a = ap.parse_args()
    asyncio.run(main(a.n, a.base))
