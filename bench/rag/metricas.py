"""Pasos 2.6.5 a 2.6.7: Recall@K, MRR, estudio del umbral y mezcla entre asignaturas.

Criterio estricto: acierto si aparece la diapositiva etiquetada. Criterio ±1: también vale la anterior
o la siguiente del mismo PDF (una idea suele ocupar dos diapositivas seguidas).
Uso: python bench/rag/metricas.py   (imprime y escribe resultados/<entorno>/rag_metricas.csv)
"""
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

AQUI = os.path.dirname(os.path.abspath(__file__))
UMBRAL_PRODUCCION, K_PRODUCCION = 0.40, 3


def cargar(entorno_dir: str = None):
    with open(os.path.join(AQUI, "preguntas.csv"), encoding="utf-8") as f:
        preguntas = {p["id"]: p for p in csv.DictReader(f)}
    _, filas = c.leer_csv(os.path.join(entorno_dir or c.RESULTADOS, "rag_resultados.csv"))
    res = collections.defaultdict(list)
    for f in filas:
        if f["puesto"] != "0":
            res[f["id"]].append(f)
    for v in res.values():
        v.sort(key=lambda f: int(f["puesto"]))
    return preguntas, res


def puesto_acierto(p: dict, resultados: list, umbral: float, margen: int):
    """Puesto (1..n) del primer resultado correcto entre los que superan el umbral, o None."""
    validos = [r for r in resultados if float(r["similitud"]) > umbral]
    for i, r in enumerate(validos, start=1):
        if r["tema"] == p["tema"] and abs(int(r["diapositiva"]) - int(p["diapositiva"])) <= margen:
            return i
    return None


def metricas(preguntas: dict, res: dict, ids: list, umbral: float, margen: int) -> dict:
    puestos = [puesto_acierto(preguntas[i], res.get(i, []), umbral, margen) for i in ids]
    n = len(ids)
    m = {f"recall@{k}": sum(1 for x in puestos if x and x <= k) / n for k in (1, 3, 5)}
    m["mrr"] = sum(1 / x for x in puestos if x and x <= 10) / n
    m["sin_resultado"] = sum(1 for i in ids if not [r for r in res.get(i, []) if float(r["similitud"]) > umbral]) / n
    m["n"] = n
    return m


def mezcla(preguntas: dict, res: dict, ids: list) -> dict:
    """Con la configuración de producción (umbral 0,40 y 3 resultados): ¿cuántas consultas traen otra asignatura?"""
    top1 = alguna = 0
    for i in ids:
        validos = [r for r in res.get(i, []) if float(r["similitud"]) > UMBRAL_PRODUCCION][:K_PRODUCCION]
        if validos and validos[0]["asignatura"] != preguntas[i]["asignatura"]:
            top1 += 1
        if any(r["asignatura"] != preguntas[i]["asignatura"] for r in validos):
            alguna += 1
    return {"top1_otra_asignatura": top1 / len(ids), "alguna_otra_asignatura": alguna / len(ids), "n": len(ids)}


def main() -> None:
    preguntas, res = cargar()
    todos = sorted(preguntas)
    out = c.Csv("rag_metricas", ["grupo", "valor", "criterio", "umbral", "n", "recall@1", "recall@3", "recall@5", "mrr",
                                 "sin_resultado", "top1_otra_asignatura", "alguna_otra_asignatura"],
                {"origen": "rag_resultados.csv", "preguntas": len(todos)})
    grupos = [("total", "todas", todos)]
    grupos += [("asignatura", a, [i for i in todos if preguntas[i]["asignatura"] == a]) for a in ("FP", "MP", "FS")]
    grupos += [("tipo", t, [i for i in todos if preguntas[i]["tipo"] == t]) for t in ("teoria", "codigo", "erratas", "ambigua")]
    for grupo, valor, ids in grupos:
        for criterio, margen in (("estricto", 0), ("mas_menos_1", 1)):
            for umbral in (0.0, 0.30, 0.40, 0.50):
                m = metricas(preguntas, res, ids, umbral, margen)
                extra = mezcla(preguntas, res, ids) if (umbral == UMBRAL_PRODUCCION and criterio == "estricto") else {}
                fila = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in {**m, **extra}.items()}
                out.fila(grupo=grupo, valor=valor, criterio=criterio, umbral=umbral, **fila)
                if umbral in (0.0, 0.40):
                    print(f"{grupo:10} {valor:8} {criterio:12} u={umbral:.2f} " + " ".join(
                        f"{k}={v:.3f}" for k, v in {**m, **extra}.items() if k != "n"))
    out.cerrar()


if __name__ == "__main__":
    main()
