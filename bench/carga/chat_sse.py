"""Carga sobre /api/chat/stream leyendo el flujo SSE: TTFT y duración total por petición (paso 2.5.1).

k6 no lee el cuerpo en streaming, así que el TTFT bajo carga se mide con este cliente asyncio.
Cada cliente manda un saludo cada 5 s (12 por minuto, bajo el límite de 15 por minuto).
Uso: python bench/carga/chat_sse.py --url http://127.0.0.1:8100 --clientes 10 --duracion 180 --rep 1
"""
import argparse
import asyncio
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

CUERPO = {"historial": [{"role": "user", "content": "hola buenas tardes"}], "archivos": {}, "asignatura": "cpp"}


async def cliente(i: int, url: str, fin: float, out, clientes: int, rep: int, http: httpx.AsyncClient, pausa: float):
    cab = {"X-Forwarded-For": f"10.7.{i // 250}.{i % 250}"}
    await asyncio.sleep(pausa * i / clientes)  # arranques repartidos dentro del primer ciclo
    while time.monotonic() < fin:
        t0 = time.perf_counter()
        ttft = total = None
        estado = "sin_respuesta"
        try:
            async with http.stream("POST", f"{url}/api/chat/stream", json=CUERPO, headers=cab) as r:
                estado = str(r.status_code)
                if r.status_code == 200:
                    async for linea in r.aiter_lines():
                        if linea.startswith("data:"):
                            if ttft is None:
                                ttft = (time.perf_counter() - t0) * 1000
                            if "[DONE]" in linea:
                                break
                            if '"error"' in linea:
                                estado = "error_stream"
            total = (time.perf_counter() - t0) * 1000
        except Exception as e:
            estado = type(e).__name__
        out.fila(clientes=clientes, rep=rep, t_s=round(time.monotonic(), 2), estado=estado,
                 ttft_ms="" if ttft is None else round(ttft, 2), total_ms="" if total is None else round(total, 2))
        await asyncio.sleep(pausa)


async def main(a) -> None:
    out = c.Csv("carga_chat", ["clientes", "rep", "t_s", "estado", "ttft_ms", "total_ms"],
                {"llm": "simulado (100 ms al primer token, 20 ms por palabra)", "cliente": "portatil por tunel SSH"},
                reanudar=True)
    limites = httpx.Limits(max_connections=a.clientes + 5)
    async with httpx.AsyncClient(timeout=60, limits=limites) as http:
        fin = time.monotonic() + a.duracion
        await asyncio.gather(*(cliente(i, a.url, fin, out, a.clientes, a.rep, http, a.pausa) for i in range(a.clientes)))
    out.cerrar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8100")
    ap.add_argument("--clientes", type=int, default=10)
    ap.add_argument("--duracion", type=int, default=180)
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--pausa", type=float, default=5.0)
    asyncio.run(main(ap.parse_args()))
