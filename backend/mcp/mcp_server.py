"""Servidor MCP del tutor (FastMCP, transporte stdio).

Lo lanza tutor.py como proceso hijo y expone las tres herramientas del agente. Importante: en stdio
el protocolo usa stdout, así que nada de este proceso puede imprimir ahí (los logs van a stderr).
"""
import sys
import os
import asyncio
from contextlib import asynccontextmanager

# Aseguramos que Python encuentre la carpeta 'services'
DIRECTORIO_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DIRECTORIO_BACKEND not in sys.path:
    sys.path.insert(0, DIRECTORIO_BACKEND)

from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from services.search import async_search_theory_logic
from services.compiler import compile_and_run_project
from services.warm_pool import pool


@asynccontextmanager
async def lifespan(_server: FastMCP):
    # Pool de contenedores propio de este proceso (prefijo tutor_mcp_, ver WARM_POOL_PREFIX)
    try:
        await pool.start_pool()
    except Exception as e:
        print(f"⚠️ [MCP] No se pudo iniciar el Warm Pool: {e}", file=sys.stderr, flush=True)
    try:
        yield
    finally:
        await pool.stop_pool()


mcp = FastMCP("TutorIA_Workspace", lifespan=lifespan)


@mcp.tool()
async def compilar_cpp(archivos: dict[str, str]) -> str:
    """
    Compila y ejecuta el proyecto C++ actual del alumno dentro del sandbox seguro de Docker.
    USO: Solo si el alumno pide explícitamente ejecutar su código o pregunta por qué da error de compilación.
    """
    resultado = await compile_and_run_project(archivos)
    return resultado["output"]


@mcp.tool()
async def buscar_apuntes_ugr(pregunta: str) -> str:
    """
    Busca en la base de datos de apuntes oficiales de la UGR mediante pgvector.
    USO OBLIGATORIO: Cuando el alumno pregunta teoría, temario o conceptos de C++ o Linux.
    NO USAR para saludos ni para corregir código sin dudas teóricas.
    """
    return await async_search_theory_logic(pregunta)


def _buscar_en_web(consulta: str) -> str:
    try:
        resultados = DDGS().text(consulta, max_results=3)
        if not resultados:
            return "Sin resultados en internet."
        texto = "Resultados web:\n"
        for r in resultados:
            texto += f"- {r.get('title', '')}: {r.get('body', '')}\n"
        return texto
    except Exception as e:
        return f"Búsqueda web no disponible: {str(e)}"


@mcp.tool()
async def buscar_internet(consulta: str) -> str:
    """
    Busca información en internet mediante DuckDuckGo si el concepto no está en los apuntes UGR.
    """
    return await asyncio.to_thread(_buscar_en_web, consulta)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
