"""¿Quedan terminales huérfanas si la API muere con sesiones abiertas?

En la VM había cinco contenedores de la imagen del sandbox con tty, sin límites y como root, vivos desde
semanas antes: terminales de una versión anterior cuyo cliente `docker run` desapareció. Este script arranca la
API en local, abre una terminal por WebSocket, mata la API con SIGKILL (como un reinicio forzado de pm2 o una
caída) y mira si el contenedor sigue vivo pasado un tiempo.

Después arranca la API otra vez (como un reinicio de pm2) y mira si la terminal huérfana sigue viva: con el
arreglo de F-7 el arranque la borra.

Uso: python bench/seguridad/terminal_huerfana.py [--n 5] [--espera 20]
"""
import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time

import websockets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

PUERTO = 8198
PREFIJO = "bench_huer_term_"


def terminales() -> list:
    r = subprocess.run(["docker", "ps", "--filter", f"name={PREFIJO}", "--format", "{{.Names}}"], capture_output=True, text=True)
    return r.stdout.split()


ENV = {**os.environ, "WARM_POOL_PREFIX": "bench_huer_", "WARM_POOL_SIZE": "1", "TUTOR_MCP_EAGER": "0",
       "TERMINAL_PREFIX": PREFIJO}


def arrancar_api():
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(PUERTO)], cwd=c.BACKEND_DIR,
                            env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


async def esperar_api() -> None:
    for _ in range(120):
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://127.0.0.1:{PUERTO}/docs"],
                           capture_output=True, text=True)
        if r.stdout == "200":
            return
        await asyncio.sleep(1)


async def una(rep: int, espera: float, out: c.Csv) -> None:
    antes = set(terminales())
    api = arrancar_api()
    api2 = None
    try:
        for _ in range(120):
            try:
                ws = await websockets.connect(f"ws://127.0.0.1:{PUERTO}/ws/terminal", open_timeout=5)
                break
            except Exception:
                await asyncio.sleep(1)
        buf = ""
        while "$" not in buf:
            buf += await asyncio.wait_for(ws.recv(), timeout=40)
        nuevas = [t for t in terminales() if t not in antes]
        os.kill(api.pid, signal.SIGKILL)  # solo el proceso de la API: sus hijos siguen como tras un kill de pm2
        t0 = time.perf_counter()
        await asyncio.sleep(espera)
        vivas = [t for t in terminales() if t in nuevas]
        api2 = arrancar_api()  # reinicio, como haría pm2
        await esperar_api()
        tras_reinicio = [t for t in terminales() if t in nuevas]
        out.fila(rep=rep, terminal_abierta=int(bool(nuevas)), espera_s=espera, sigue_viva=int(bool(vivas)),
                 segundos=round(time.perf_counter() - t0, 1), viva_tras_reiniciar=int(bool(tras_reinicio)))
        print(rep, nuevas, "viva" if vivas else "borrada", "| tras reiniciar:", "viva" if tras_reinicio else "borrada", flush=True)
        try:
            await ws.close()
        except Exception:
            pass
    finally:
        for p in (api, api2):
            if p is None:
                continue
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for t in set(terminales()) - antes:
            subprocess.run(["docker", "rm", "-f", t], capture_output=True)
        subprocess.run(["docker", "rm", "-f", "bench_huer_0"], capture_output=True)


async def main(a) -> None:
    out = c.Csv("seguridad_terminal_huerfana", ["rep", "terminal_abierta", "espera_s", "sigue_viva", "segundos",
                                                 "viva_tras_reiniciar"],
                {"senal": "SIGKILL a la API"})
    for rep in range(a.n):
        await una(rep, a.espera, out)
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--espera", type=float, default=20)
    asyncio.run(main(ap.parse_args()))
