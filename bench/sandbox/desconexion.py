"""Paso 2.3.3: qué pasa si el alumno cierra la página a mitad de una ejecución.

Arranca la API en local con un pool propio de 1 contenedor, manda un bucle infinito a /api/execute y corta la
conexión a los 3 s. Después mira el contenedor desde el host: si el programa sigue vivo, cuándo muere, cuándo se
recrea el contenedor y si la siguiente petición funciona. Es una medida de comportamiento, no de latencia.

Uso: python bench/sandbox/desconexion.py [--n 10]   (SANDBOX_NO_NEW_PRIVILEGES=0 en hosts que no lo admiten)
"""
import argparse
import asyncio
import os
import subprocess
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

PUERTO = 8199
URL = f"http://127.0.0.1:{PUERTO}"
NOMBRE = "bench_desc_0"
BUCLE = {"archivos": {"main.cpp": "int main() { volatile unsigned long x = 0; while (true) ++x; }\n"}}
HOLA = {"archivos": {"main.cpp": "#include <iostream>\nint main() { std::cout << \"hola\"; }\n"}}
CORTE_S = 3.0


def contenedor_id() -> str:
    r = subprocess.run(["docker", "inspect", "-f", "{{.Id}} {{.State.Running}}", NOMBRE], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def programa_vivo() -> bool:
    r = subprocess.run(["docker", "top", NOMBRE], capture_output=True, text=True)
    return r.returncode == 0 and "programa.out" in r.stdout


async def esperar_api() -> None:
    async with httpx.AsyncClient() as h:
        for _ in range(120):
            try:
                await h.get(URL + "/docs")
                if contenedor_id().endswith("true"):
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    raise RuntimeError("la API no arrancó")


async def una(rep: int, out: c.Csv) -> None:
    for _ in range(120):  # que el contenedor de la repetición anterior ya esté recreado y libre
        if contenedor_id().endswith("true") and not programa_vivo():
            break
        await asyncio.sleep(0.5)
    await asyncio.sleep(2)
    id0 = contenedor_id().split()[0]
    async with httpx.AsyncClient(timeout=60, headers={"X-Forwarded-For": f"10.77.0.{rep + 1}"}) as h:
        tarea = asyncio.create_task(h.post(URL + "/api/execute", json=BUCLE))
        await asyncio.sleep(CORTE_S)
        vivo_antes = programa_vivo()
        tarea.cancel()  # cierra la conexión, como al cerrar la pestaña
        try:
            await tarea
        except (asyncio.CancelledError, httpx.HTTPError):
            pass
    t_corte = time.perf_counter()
    vivo_tras_2s, muere_ms, recreado_ms = None, "", ""
    while time.perf_counter() - t_corte < 45:
        dt = (time.perf_counter() - t_corte) * 1000
        vivo = programa_vivo()
        if vivo_tras_2s is None and dt >= 2000:
            vivo_tras_2s = vivo
        if not vivo and muere_ms == "":
            muere_ms = round(dt)
        estado = contenedor_id()
        if estado and estado.split()[0] != id0 and estado.endswith("true"):
            recreado_ms = round(dt)
            break
        await asyncio.sleep(0.25)
    async with httpx.AsyncClient(timeout=60, headers={"X-Forwarded-For": f"10.78.0.{rep + 1}"}) as h:
        t0 = time.perf_counter()
        r = await h.post(URL + "/api/execute", json=HOLA)
        sig_ms = round((time.perf_counter() - t0) * 1000)
        sig_ok = r.status_code == 200 and "hola" in r.json().get("output", "")
    out.fila(rep=rep, corte_s=CORTE_S, programa_vivo_al_cortar=int(vivo_antes), programa_vivo_2s_despues=int(bool(vivo_tras_2s)),
             ms_hasta_que_muere=muere_ms, ms_hasta_recrear=recreado_ms, siguiente_ok=int(sig_ok), siguiente_ms=sig_ms)
    print(rep, vivo_antes, vivo_tras_2s, muere_ms, recreado_ms, sig_ok, sig_ms, flush=True)


async def main(a) -> None:
    env = {**os.environ, "WARM_POOL_PREFIX": "bench_desc_", "WARM_POOL_SIZE": "1", "TUTOR_MCP_EAGER": "0"}
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(PUERTO)], cwd=c.BACKEND_DIR, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await esperar_api()
        out = c.Csv("sandbox_desconexion", ["rep", "corte_s", "programa_vivo_al_cortar", "programa_vivo_2s_despues",
                                            "ms_hasta_que_muere", "ms_hasta_recrear", "siguiente_ok", "siguiente_ms"],
                    {"timeout_ejecucion_s": 30, "tam_pool": 1})
        for rep in range(a.n):
            await una(rep, out)
        out.cerrar()
    finally:
        api.terminate()
        api.wait(timeout=60)
        subprocess.run(["docker", "rm", "-f", NOMBRE], capture_output=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    asyncio.run(main(ap.parse_args()))
