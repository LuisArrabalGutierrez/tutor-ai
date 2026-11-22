"""Pasos 2.8.3 y 2.8.6: lanza los prompts de fuga contra el tutor, 3 veces cada uno.

La condición la fija TUTOR_GRAPH antes de arrancar: 1 = grafo con guardrails, 0 = agente prefabricado
(solo el prompt). Cada condición va en su propio proceso y en su propio CSV. Reanudable.
Uso: TUTOR_GRAPH=1 python bench/tutor/fuga.py     y     TUTOR_GRAPH=0 python bench/tutor/fuga.py
"""
import argparse
import asyncio
import csv
import os

from _agente import CuotaAgotada, MODELOS, c, guardar_privado, preguntar
import tutor

AQUI = os.path.dirname(os.path.abspath(__file__))
REPS = 3


async def main(pausa: float, limite: int) -> None:
    cond = "con_guardrail" if tutor._graph_enabled() else "sin_guardrail"
    nombre = f"tutor_fuga_{cond}"
    with open(os.path.join(AQUI, "fuga_prompts.csv"), encoding="utf-8") as f:
        prompts = list(csv.DictReader(f))
    ya = c.hechas(nombre, "id", "rep")
    out = c.Csv(nombre, ["id", "categoria", "asignatura", "rep", "ms", "herramientas", "inyeccion_detectada", "sospecha",
                         "juez_interno", "reescrita", "mensaje_fijo", "bloques_codigo", "lineas_codigo_max", "error"],
                {**MODELOS, "condicion": cond}, reanudar=True)
    hechas = 0
    try:
        for rep in range(REPS):
            for p in prompts:
                if (p["id"], str(rep)) in ya:
                    continue
                if limite and hechas >= limite:
                    return
                try:
                    r = await preguntar(p["consulta"], p["asignatura"], p["proyecto"])
                except CuotaAgotada as q:
                    print("Cuota agotada, se para aquí:", q)
                    return
                except Exception as ex:
                    print(p["id"], rep, "error", type(ex).__name__, str(ex)[:100], flush=True)
                    await asyncio.sleep(pausa)
                    continue  # sin fila: se reintenta en la próxima pasada
                g = r["guard"]
                bloques = c_bloques(r["texto"])
                out.fila(id=p["id"], categoria=p["categoria"], asignatura=p["asignatura"], rep=rep, ms=round(r["ms"]),
                         herramientas="+".join(r["herramientas"]) or "ninguna",
                         inyeccion_detectada=int(bool(g.get("injection"))), sospecha=int(bool(g.get("suspicious"))),
                         juez_interno=g.get("judge", ""), reescrita=int(bool(g.get("rewritten"))),
                         mensaje_fijo=int(bool(g.get("fallback"))), bloques_codigo=len(bloques),
                         lineas_codigo_max=max(bloques, default=0))
                guardar_privado(f"fuga_{cond}", {"id": p["id"], "rep": rep, "categoria": p["categoria"],
                                                 "asignatura": p["asignatura"], "proyecto": p["proyecto"],
                                                 "consulta": p["consulta"], "texto": r["texto"], "guard": g})
                hechas += 1
                print(cond, p["id"], rep, flush=True)
                await asyncio.sleep(pausa)
    finally:
        out.cerrar()
        await tutor.stop_tutor_runtime()


def c_bloques(texto: str) -> list:
    import guardrails
    return [len(b.lines) for b in guardrails.code_blocks(texto)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pausa", type=float, default=9)
    ap.add_argument("--limite", type=int, default=0, help="máximo de respuestas en esta pasada (0 = sin tope)")
    a = ap.parse_args()
    asyncio.run(main(a.pausa, a.limite))
