"""Paso 2.7.5: qué pasa cuando Gemini falla. Se arranca el tutor con una clave de Gemini inválida y se
mide si responde Groq y cuánto tarda, frente al mismo proceso con la clave buena.

Cada caso va en su propio proceso, porque la clave se lee al importar `tutor`:
  python bench/tutor/fallback.py normal        y        python bench/tutor/fallback.py gemini_caida
"""
import asyncio
import contextlib
import io
import os
import sys

CASO = sys.argv[1] if len(sys.argv) > 1 else "normal"
if CASO == "gemini_caida":
    os.environ["GOOGLE_API_KEY"] = "clave-invalida-para-la-prueba-de-caida"

from _agente import MODELOS, PROYECTOS, c  # noqa: E402
import tutor  # noqa: E402

CONSULTA = "no sé por qué mi media sale sin decimales, ¿me das una pista?"
N = 10


async def main() -> None:
    out = c.Csv("tutor_fallback", ["caso", "rep", "ms", "respondio", "paso_a_groq", "caracteres"], MODELOS, reanudar=True)
    try:
        for rep in range(N):
            salida = io.StringIO()
            with c.Crono() as t, contextlib.redirect_stdout(salida):
                texto = await tutor.get_socratic_response_async([{"role": "user", "content": CONSULTA}], PROYECTOS["media"], "", "cpp")
            registro = salida.getvalue()
            out.fila(caso=CASO, rep=rep, ms=round(t.ms), respondio=int(bool(texto) and "no está disponible" not in texto and "ha ocurrido un error" not in texto),
                     paso_a_groq=int("Fallback a Secundario" in registro), caracteres=len(texto))
            print(CASO, rep, round(t.ms), "groq" if "Fallback a Secundario" in registro else "primario", flush=True)
            await asyncio.sleep(8)
    finally:
        out.cerrar()
        await tutor.stop_tutor_runtime()


if __name__ == "__main__":
    asyncio.run(main())
