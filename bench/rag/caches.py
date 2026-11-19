"""Paso 2.6.8: efecto de las dos cachés de `services/search.py` en la latencia.

Para cada pregunta: sin cachés, con la caché de resultado, y solo con la de embedding (se vacía la de
resultado). Usa el código real del backend.
Uso: python bench/rag/caches.py [--n 30]
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from services import search  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    n = ap.parse_args().n
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "preguntas.csv"), encoding="utf-8") as f:
        preguntas = [p for p in csv.DictReader(f) if p["tipo"] == "teoria"][:n]
    out = c.Csv("rag_caches", ["id", "caso", "ms"], {"n": len(preguntas)})
    for p in preguntas:
        # Sufijo para que la pregunta no esté ya en ninguna caché de este proceso
        q = p["pregunta"]
        with c.Crono() as t:
            search.search_theory_logic(q)
        out.fila(id=p["id"], caso="sin_cache", ms=round(t.ms, 2))
        with c.Crono() as t:
            search.search_theory_logic(q)
        out.fila(id=p["id"], caso="cache_resultado", ms=round(t.ms, 4))
        search._RESULT_CACHE.clear()
        with c.Crono() as t:
            search.search_theory_logic(q)
        out.fila(id=p["id"], caso="cache_embedding", ms=round(t.ms, 2))
        time.sleep(0.7)
    out.cerrar()
