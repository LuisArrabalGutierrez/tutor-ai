import sys
import os
import json

# Configura ruta
DIRECTORIO_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIRECTORIO_BACKEND)

from mcp.server.fastmcp import FastMCP
from services.search import search_theory_logic 
from services.compiler import compile_and_run_project
from duckduckgo_search import DDGS

mcp = FastMCP("TutorIA_Workspace")

@mcp.tool()
def compilar_cpp() -> str:
    """Compila y ejecuta el proyecto C++. No usar para teoria."""
    try:
        # Lee proyecto
        ruta_json = os.path.join(DIRECTORIO_BACKEND, "temp_project.json")
        with open(ruta_json, "r", encoding="utf-8") as f:
            archivos_proyecto = json.load(f)
            
        resultado = compile_and_run_project(archivos_proyecto)
        return resultado["output"]
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def buscar_apuntes_ugr(pregunta: str) -> str:
    """Busca apuntes. Usar siempre para teoria o conceptos."""
    return search_theory_logic(pregunta)

@mcp.tool()
def buscar_internet(consulta: str) -> str:
    """Busca en internet."""
    try:
        resultados = DDGS().text(consulta, max_results=3)
        if not resultados:
            return "Sin resultados."
        texto = "Resultados:\n"
        for r in resultados:
            texto += f"- {r['title']}: {r['body']}\n"
        return texto
    except Exception as e:
        return f"Error: {e}"

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()