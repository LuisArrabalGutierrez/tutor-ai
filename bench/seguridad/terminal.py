"""Paso 2.4.4: ataques contra la terminal Linux, por el mismo WebSocket que usa el alumno.

Se ejecuta en la máquina donde corre la instancia de pruebas (necesita `docker stats`).
Uso: python bench/seguridad/terminal.py --url ws://127.0.0.1:8100 [--n 10]
"""
import argparse
import asyncio
import os
import re
import subprocess
import sys
import time

import websockets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

# nombre, orden, segundos de observación, mecanismo esperado
ATAQUES = [
    ("red", "timeout 5 bash -c 'echo > /dev/tcp/8.8.8.8/53' 2>/dev/null && echo RED_OK || echo RED_FALLA", 8, "--network none"),
    ("bomba_fork", ":(){ :|:& };:", 12, "--pids-limit 100"),
    ("memoria", "tail /dev/zero; echo FIN_MEM rc=$?", 40, "--memory 512m"),
    ("disco", "dd if=/dev/zero of=/tmp/relleno bs=1M count=1024 2>&1 | tail -1; echo DD_RC=${PIPESTATUS[0]}", 60, "ninguno previsto"),
    ("cpu", "for i in 1 2 3 4; do (while :; do :; done) & done; echo LANZADOS", 12, "--cpus 1"),
]


def contenedor_terminal() -> str:
    r = subprocess.run(["docker", "ps", "--filter", "name=tutor_term_", "--format", "{{.Names}}"], capture_output=True, text=True)
    return (r.stdout.split() or [""])[0]


def stats(nombre: str):
    r = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}} {{.MemUsage}} {{.PIDs}}", nombre],
                       capture_output=True, text=True)
    try:
        p = r.stdout.split()
        m = re.match(r"([\d.]+)(\w+)", p[1])
        mb = float(m.group(1)) * {"B": 1 / 1048576, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[m.group(2)]
        return float(p[0].rstrip("%")), mb, int(p[-1])
    except Exception:
        return 0.0, 0.0, 0


async def leer(ws, hasta: str, segundos: float) -> str:
    buf, fin = "", time.monotonic() + segundos
    while hasta not in buf and time.monotonic() < fin:
        try:
            buf += await asyncio.wait_for(ws.recv(), timeout=max(0.1, fin - time.monotonic()))
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            break
    return buf


async def una(url: str, nombre: str, orden: str, segundos: int) -> dict:
    cpu_max = mem_max = 0.0
    pids_max = 0
    async with websockets.connect(url + "/ws/terminal", open_timeout=30, max_size=None) as ws:
        await leer(ws, "$", 40)
        cont = contenedor_terminal()
        await ws.send(orden + "\n")
        salida, fin = "", time.monotonic() + segundos
        marca = {"red": "RED_", "memoria": "FIN_MEM", "disco": "DD_RC=", "cpu": "\x00", "bomba_fork": "\x00"}[nombre]
        while time.monotonic() < fin:
            salida += await leer(ws, marca, 1.0)
            cpu, mem, pids = await asyncio.to_thread(stats, cont)
            cpu_max, mem_max, pids_max = max(cpu_max, cpu), max(mem_max, mem), max(pids_max, pids)
            # La orden tecleada también contiene la marca: se busca en lo que viene después del eco
            if nombre in ("red", "memoria", "disco") and re.search(r"RED_(OK|FALLA)\s|FIN_MEM rc=\d|DD_RC=\d", salida.split("\n", 1)[-1]):
                break
    await asyncio.sleep(3)
    sigue = bool(subprocess.run(["docker", "ps", "-q", "--filter", f"name={cont}"], capture_output=True, text=True).stdout.strip())
    return {"salida": salida, "cpu_max": cpu_max, "mem_max": mem_max, "pids_max": pids_max, "contenedor_borrado": int(not sigue)}


def veredicto(nombre: str, r: dict):
    s = r["salida"].split("\n", 1)[-1]
    if nombre == "red":
        return "RED_OK" not in s, "conexión rechazada" if "RED_FALLA" in s else s[-60:]
    if nombre == "bomba_fork":
        return r["pids_max"] <= 100, f"pids_max={r['pids_max']}"
    if nombre == "memoria":
        m = re.search(r"FIN_MEM rc=(\d+)", s)
        return bool(m) and m.group(1) == "137" and r["mem_max"] <= 520, f"rc={m.group(1) if m else '?'} mem_contenedor_max={r['mem_max']:.0f}MiB"
    if nombre == "disco":
        m = re.search(r"DD_RC=(\d+)", s)
        escrito = re.search(r"(\d+) bytes", s)
        return bool(m) and m.group(1) != "0", f"dd_rc={m.group(1) if m else '?'} bytes={escrito.group(1) if escrito else '?'}"
    return r["cpu_max"] <= 130, f"cpu_contenedor_max={r['cpu_max']:.0f}%"


async def main(a) -> None:
    out = c.Csv("seguridad_terminal", ["ataque", "rep", "contenido", "mecanismo", "evidencia", "cpu_max", "mem_max_mb",
                                       "pids_max", "contenedor_borrado"], {"objetivo": "terminal por WebSocket"})
    for nombre, orden, segundos, mecanismo in ATAQUES:
        for rep in range(a.n):
            try:
                r = await una(a.url, nombre, orden, segundos)
                ok, evidencia = veredicto(nombre, r)
            except Exception as e:
                r, ok, evidencia = {"cpu_max": 0, "mem_max": 0, "pids_max": 0, "contenedor_borrado": ""}, False, f"error: {type(e).__name__}"
            out.fila(ataque=nombre, rep=rep, contenido=int(ok), mecanismo=mecanismo, evidencia=evidencia,
                     cpu_max=round(r["cpu_max"], 1), mem_max_mb=round(r["mem_max"], 1), pids_max=r["pids_max"],
                     contenedor_borrado=r["contenedor_borrado"])
            print(nombre, rep, "CONTENIDO" if ok else "NO CONTENIDO", evidencia, flush=True)
            await asyncio.sleep(2)
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8100")
    ap.add_argument("--n", type=int, default=10)
    asyncio.run(main(ap.parse_args()))
