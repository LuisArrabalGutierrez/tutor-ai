import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import tutor


def _run(coro):
    return asyncio.run(coro)


async def _con_runtime(prueba):
    await tutor.start_tutor_runtime()
    try:
        return await prueba({t.name: t for t in tutor._runtime.tools})
    finally:
        await tutor.stop_tutor_runtime()


def test_el_servidor_mcp_expone_las_tres_herramientas():
    async def prueba(tools):
        assert set(tools) == {"compilar_cpp", "buscar_apuntes_ugr", "buscar_internet"}
        # Al LLM se le ofrece compilar_cpp sin parámetros: el proyecto no lo decide el modelo
        assert tools["compilar_cpp"].args == {}
    _run(_con_runtime(prueba))


def test_compilar_cpp_usa_el_proyecto_del_contexto_y_el_pool_del_mcp():
    async def prueba(tools):
        token = tutor._current_project_context.set(
            {"main.cpp": '#include <iostream>\nint main(){ std::cout << "via MCP"; }'}
        )
        try:
            salida = await tools["compilar_cpp"].ainvoke({})
        finally:
            tutor._current_project_context.reset(token)
        assert "via MCP" in salida
    _run(_con_runtime(prueba))


def test_compilar_cpp_sin_proyecto_devuelve_error_claro():
    async def prueba(tools):
        salida = await tools["compilar_cpp"].ainvoke({})
        assert "No hay archivos" in salida
    _run(_con_runtime(prueba))


def test_el_proceso_mcp_no_ensucia_stdout():
    """Si algo imprime en stdout del servidor, el protocolo JSON-RPC se corrompe y no hay herramientas."""
    async def prueba(tools):
        assert tutor._runtime.mcp_ok is True
    _run(_con_runtime(prueba))
