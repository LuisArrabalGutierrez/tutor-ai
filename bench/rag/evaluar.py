"""Paso 2.6.4: lanza cada pregunta contra `match_apuntes` y guarda los 10 primeros resultados.

Reproduce lo que hace `services/search.py`: la pregunta en minúsculas, `gemini-embedding-001` con
RETRIEVAL_QUERY y 768 dimensiones. Se pide con umbral 0 y 10 resultados para poder estudiar después
otros umbrales y valores de K sin gastar más cuota. Reanudable.
Uso: python bench/rag/evaluar.py
"""
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(c.BACKEND_DIR, ".env"))
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402
from supabase import create_client  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = "gemini-embedding-001"
TOP = 10


def main() -> None:
    google = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    with open(os.path.join(AQUI, "preguntas.csv"), encoding="utf-8") as f:
        preguntas = list(csv.DictReader(f))
    ya = {k[0] for k in c.hechas("rag_resultados", "id")}
    out = c.Csv("rag_resultados", ["id", "puesto", "tema", "asignatura", "diapositiva", "similitud", "embedding_ms", "rpc_ms"],
                {"modelo_embedding": MODELO, "dimensiones": 768, "umbral_consulta": 0.0, "top": TOP}, reanudar=True)
    for p in preguntas:
        if p["id"] in ya:
            continue
        with c.Crono() as t_emb:
            emb = google.models.embed_content(
                model=MODELO, contents=p["pregunta"].strip().lower(),
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=768))
        vector = list(emb.embeddings[0].values)
        with c.Crono() as t_rpc:
            res = sb.rpc("match_apuntes", {"query_embedding": vector, "match_threshold": 0.0, "match_count": TOP}).execute()
        for puesto, fila in enumerate(res.data, start=1):
            out.fila(id=p["id"], puesto=puesto, tema=fila["tema"], asignatura=fila["asignatura"],
                     diapositiva=fila["diapositiva"], similitud=round(fila["similarity"], 4),
                     embedding_ms=round(t_emb.ms, 1), rpc_ms=round(t_rpc.ms, 1))
        if not res.data:
            out.fila(id=p["id"], puesto=0, embedding_ms=round(t_emb.ms, 1), rpc_ms=round(t_rpc.ms, 1))
        print(p["id"], len(res.data), flush=True)
        time.sleep(0.7)  # 100 peticiones por minuto en la capa gratuita
    out.cerrar()


if __name__ == "__main__":
    main()
