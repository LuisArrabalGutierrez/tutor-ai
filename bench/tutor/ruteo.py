"""Pasos 2.7.1 a 2.7.3 y 2.7.6: qué herramienta elige el tutor en cada escenario y qué formato devuelve.

Uso: python bench/tutor/ruteo.py [--pausa 8]      (reanudable; para al agotarse la cuota)
"""
import argparse
import asyncio
import csv
import json
import os
import re
import sys

from _agente import CuotaAgotada, MODELOS, c, guardar_privado, preguntar
import tutor

AQUI = os.path.dirname(os.path.abspath(__file__))
NOMBRE = {"buscar_apuntes_ugr": "apuntes", "compilar_cpp": "compilar", "buscar_internet": "internet"}
HTML_RE = re.compile(r"</?(?:p|div|span|br|b|i|u|strong|em|ul|ol|li|h[1-6]|table|a)\b[^>]*>", re.I)


async def main(pausa: float) -> None:
    with open(os.path.join(AQUI, "escenarios.csv"), encoding="utf-8") as f:
        escenarios = list(csv.DictReader(f))
    ya = {k[0] for k in c.hechas("tutor_ruteo", "id")}
    out = c.Csv("tutor_ruteo", ["id", "asignatura", "esperada", "primera", "todas", "acierto_primera", "acierto_incluida",
                                "ruta", "ms", "html_antes", "enlaces_quitados", "html_despues", "cita_oficial",
                                "termina_en_pregunta", "error"], MODELOS, reanudar=True)
    try:
        for e in escenarios:
            if e["id"] in ya:
                continue
            try:
                r = await preguntar(e["consulta"], e["asignatura"], e["proyecto"])
            except CuotaAgotada as q:
                print("Cuota agotada, se para aquí:", q)
                break
            except Exception as ex:
                out.fila(id=e["id"], asignatura=e["asignatura"], esperada=e["esperada"], error=type(ex).__name__ + ": " + str(ex)[:120])
                continue
            usadas = [NOMBRE.get(h, h) for h in r["herramientas"]]
            primera = usadas[0] if usadas else "ninguna"
            g = r["guard"]
            out.fila(id=e["id"], asignatura=e["asignatura"], esperada=e["esperada"], primera=primera,
                     todas="+".join(usadas) or "ninguna", acierto_primera=int(primera == e["esperada"]),
                     acierto_incluida=int(e["esperada"] in usadas or (e["esperada"] == "ninguna" and not usadas)),
                     ruta=r["ruta"], ms=round(r["ms"]), html_antes=g.get("html_fixed", ""),
                     enlaces_quitados=g.get("links_removed", ""), html_despues=len(HTML_RE.findall(r["texto"])),
                     cita_oficial=int("/storage/v1/object/public/apuntes/" in r["texto"]),
                     termina_en_pregunta=int(r["texto"].rstrip().rstrip("*_` ").endswith("?")))
            guardar_privado("ruteo_respuestas", {"id": e["id"], "consulta": e["consulta"], **r})
            print(e["id"], e["esperada"], "->", "+".join(usadas) or "ninguna", flush=True)
            await asyncio.sleep(pausa)
    finally:
        out.cerrar()
        await tutor.stop_tutor_runtime()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pausa", type=float, default=8)
    asyncio.run(main(ap.parse_args().pausa))
