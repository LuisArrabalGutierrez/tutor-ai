"""Terminal por WebSocket: latencia de apertura, de eco y de cierre, y tope de terminales (paso 2.5.1).

Uso: python bench/carga/terminal_ws.py --url ws://127.0.0.1:8100 --concurrentes 1 5 10 12 [--reps 5]
"""
import argparse
import asyncio
import os
import sys
import time

import websockets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c


async def sesion(url: str) -> dict:
    t0 = time.perf_counter()
    res = {"estado": "ok", "prompt_ms": "", "eco_ms": "", "cierre_ms": ""}
    try:
        async with websockets.connect(url + "/ws/terminal", open_timeout=30) as ws:
            buf = ""
            while "$" not in buf:  # primer prompt de bash: el contenedor ya está listo
                buf += await asyncio.wait_for(ws.recv(), timeout=40)
                if "demasiadas terminales" in buf:
                    res["estado"] = "rechazada_tope"
                    return res
            res["prompt_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            t1 = time.perf_counter()
            await ws.send("echo MARCA_$((6*7))\n")
            buf = ""
            while "MARCA_42" not in buf:
                buf += await asyncio.wait_for(ws.recv(), timeout=20)
            res["eco_ms"] = round((time.perf_counter() - t1) * 1000, 1)
            t2 = time.perf_counter()
            await ws.send("exit\n")
            try:
                while True:
                    await asyncio.wait_for(ws.recv(), timeout=20)
            except websockets.ConnectionClosed:
                pass
            res["cierre_ms"] = round((time.perf_counter() - t2) * 1000, 1)
    except Exception as e:
        res["estado"] = type(e).__name__
    return res


async def main(a) -> None:
    out = c.Csv("carga_terminal", ["concurrentes", "rep", "sesion", "estado", "prompt_ms", "eco_ms", "cierre_ms"],
                {"tope_terminales": 10})
    for k in a.concurrentes:
        for rep in range(a.reps):
            resultados = await asyncio.gather(*(sesion(a.url) for _ in range(k)))
            for i, r in enumerate(resultados):
                out.fila(concurrentes=k, rep=rep, sesion=i, **r)
            await asyncio.sleep(3)
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8100")
    ap.add_argument("--concurrentes", type=int, nargs="+", default=[1, 5, 10, 12])
    ap.add_argument("--reps", type=int, default=5)
    asyncio.run(main(ap.parse_args()))
