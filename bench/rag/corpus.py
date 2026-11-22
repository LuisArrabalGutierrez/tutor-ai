"""Tamaño del corpus del RAG (paso 4.3.5): PDFs y diapositivas indexadas por asignatura, sin copiar contenido.

Solo lectura sobre la tabla `apuntes` de Supabase. Usa las claves del `.env` del backend.
Uso: python bench/rag/corpus.py
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(c.BACKEND_DIR, ".env"))
from supabase import create_client  # noqa: E402

PAGINA = 1000


def main() -> None:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    filas, desde = [], 0
    while True:
        r = sb.table("apuntes").select("tema,asignatura,diapositiva,contenido").range(desde, desde + PAGINA - 1).execute()
        filas += r.data
        if len(r.data) < PAGINA:
            break
        desde += PAGINA
    por = collections.defaultdict(lambda: {"pdfs": set(), "diapositivas": 0, "caracteres": 0})
    for f in filas:
        a = por[f["asignatura"]]
        a["pdfs"].add(f["tema"])
        a["diapositivas"] += 1
        a["caracteres"] += len(f["contenido"] or "")
    out = c.Csv("rag_corpus", ["asignatura", "pdfs", "diapositivas", "caracteres_medios"], {"tabla": "apuntes"})
    for asig in sorted(por):
        a = por[asig]
        out.fila(asignatura=asig, pdfs=len(a["pdfs"]), diapositivas=a["diapositivas"],
                 caracteres_medios=round(a["caracteres"] / a["diapositivas"]))
    out.fila(asignatura="total", pdfs=sum(len(a["pdfs"]) for a in por.values()), diapositivas=len(filas),
             caracteres_medios=round(sum(a["caracteres"] for a in por.values()) / len(filas)))
    out.cerrar()
    print(open(out.ruta).read())


if __name__ == "__main__":
    main()
