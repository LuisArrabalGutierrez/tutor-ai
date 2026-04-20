import sys
import os
import json

# Aseguramos que Python encuentre la carpeta 'services'
DIRECTORIO_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DIRECTORIO_BACKEND not in sys.path:
    sys.path.insert(0, DIRECTORIO_BACKEND)

from mcp.server.fastmcp import FastMCP
from services.search import search_theory_logic 
from services.compiler import compile_and_run_project
from duckduckgo_search import DDGS

mcp = FastMCP("TutorIA_Workspace")

@mcp.tool()
def compilar_cpp() -> str:
    """
    Compila y ejecuta el proyecto C++ actual del alumno.
    USO: Utiliza esto SOLO cuando el alumno te pida ejecutar su código o te pregunte por qué su programa da un error de compilación.
    """
    ruta_json = os.path.join(DIRECTORIO_BACKEND, "temp_project.json")
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            archivos_proyecto = json.load(f)
        resultado = compile_and_run_project(archivos_proyecto)
        return resultado["output"]
    except Exception as e:
        return f"Error al compilar: {str(e)}"

@mcp.tool()
def buscar_apuntes_ugr(pregunta: str) -> str:
    """
    Busca en la base de datos de apuntes oficiales de la UGR. 
    USO: Obligatorio si el alumno pregunta por 'temario', 'teoría', 'dónde está explicado' o conceptos de la asignatura.
    NO USAR para corregir errores de código puntuales.
    """
    return search_theory_logic(pregunta)

@mcp.tool()
def buscar_internet(consulta: str) -> str:
    """
    Busca información en internet mediante DuckDuckGo.
    USO: SOLO usar si la respuesta no se encuentra en los apuntes oficiales de la UGR.
    """
    try:
        resultados = DDGS().text(consulta, max_results=3)
        if not resultados:
            return "Sin resultados en internet."
        texto = "Resultados web:\n"
        for r in resultados:
            texto += f"- {r.get('title', '')}: {r.get('body', '')}\n"
        return texto
    except Exception as e:
        return f"Error de conexión: {str(e)}"

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()