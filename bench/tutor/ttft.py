"""Paso 2.7.4: tiempo hasta el primer token por SSE en tres rutas, contra una API real.

Rutas: `rapida` (saludo, sin agente), `rag` (pregunta de teoría distinta cada vez, para no medir la caché)
y `compilacion` (proyecto con error de compilación). 30 repeticiones por ruta, una cada 6 s.
Uso: python bench/tutor/ttft.py --url http://127.0.0.1:8000 [--n 30]
"""
import argparse
import asyncio
import csv
import json
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

AQUI = os.path.dirname(os.path.abspath(__file__))


def cuerpos(n: int) -> dict:
    with open(os.path.join(AQUI, "proyectos.json"), encoding="utf-8") as f:
        proyectos = json.load(f)
    with open(os.path.join(c.BENCH_DIR, "rag", "preguntas.csv"), encoding="utf-8") as f:
        teoria = [p for p in csv.DictReader(f) if p["tipo"] == "teoria" and p["asignatura"] in ("MP", "FS")]
    saludos = ["hola", "buenas tardes", "hola qué tal", "buenos días", "hola tutor", "buenas"]
    msg = lambda t: [{"role": "user", "content": t}]
    return {
        "rapida": [{"historial": msg(saludos[i % len(saludos)]), "archivos": {}, "asignatura": "cpp"} for i in range(n)],
        "rag": [{"historial": msg(teoria[i % len(teoria)]["pregunta"]), "archivos": {},
                 "asignatura": "linux" if teoria[i % len(teoria)]["asignatura"] == "FS" else "cpp"} for i in range(n)],
        "compilacion": [{"historial": msg("compila mi código y dime qué pasa"),
                         "archivos": proyectos["error_compilacion"], "asignatura": "cpp"} for _ in range(n)],
    }


async def una(http: httpx.AsyncClient, url: str, cuerpo: dict, ident: str) -> dict:
    t0 = time.perf_counter()
    r = {"estado": "sin_respuesta", "ttft_ms": "", "total_ms": "", "trozos": 0, "caracteres": 0}
    try:
        async with http.stream("POST", url + "/api/chat/stream", json=cuerpo, headers={"X-Forwarded-For": ident}) as resp:
            r["estado"] = str(resp.status_code)
            async for linea in resp.aiter_lines():
                if not linea.startswith("data:"):
                    continue
                if r["ttft_ms"] == "":
                    r["ttft_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                dato = linea[5:].strip()
                if dato == "[DONE]":
                    break
                try:
                    d = json.loads(dato)
                except ValueError:
                    continue
                if "error" in d:
                    r["estado"] = "error_stream"
                r["trozos"] += 1
                r["caracteres"] += len(d.get("token", ""))
        r["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    except Exception as e:
        r["estado"] = type(e).__name__
    return r


async def main(a) -> None:
    ya = c.hechas("tutor_ttft", "ruta", "rep")
    out = c.Csv("tutor_ttft", ["ruta", "rep", "estado", "ttft_ms", "total_ms", "trozos", "caracteres"],
                {"url": "API real por tunel SSH desde el portatil", "pausa_s": a.pausa}, reanudar=True)
    async with httpx.AsyncClient(timeout=120) as http:
        for ruta, lista in cuerpos(a.n).items():
            for rep, cuerpo in enumerate(lista):
                if (ruta, str(rep)) in ya:
                    continue
                r = await una(http, a.url, cuerpo, f"10.5.0.{1 + list(('rapida', 'rag', 'compilacion')).index(ruta)}")
                out.fila(ruta=ruta, rep=rep, **r)
                print(ruta, rep, r, flush=True)
                await asyncio.sleep(a.pausa)
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--pausa", type=float, default=6)
    asyncio.run(main(ap.parse_args()))
