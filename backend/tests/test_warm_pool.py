import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from services.warm_pool import WarmPoolManager, PoolBusyError, _docker


def _run(coro):
    return asyncio.run(coro)


async def _con_pool(prueba, size=2):
    pool = WarmPoolManager(pool_size=size, prefix="tutor_test_")
    await pool.start_pool()
    try:
        return await prueba(pool)
    finally:
        await pool.stop_pool()


def test_un_contenedor_reciclado_no_conserva_estado_del_alumno_anterior():
    async def prueba(pool):
        name = await pool.get_container()
        await _docker("exec", name, "bash", "-c", "echo secreto > /tmp/huella.txt; sleep 300 &")
        pool.release(name)

        # El pool devuelve contenedores limpios: buscamos el reciclado entre los siguientes
        vistos = []
        for _ in range(pool.pool_size):
            c = await pool.get_container(timeout=20)
            vistos.append(c)
            code, out = await _docker("exec", c, "bash", "-c", "ls /tmp/huella.txt 2>&1; pgrep -f \"[s]leep 300\" || echo sin-sleep")
            assert "No such file" in out  # el archivo del alumno anterior ya no existe
            assert "sin-sleep" in out
        assert name in vistos
    _run(_con_pool(prueba))


def test_si_todos_los_contenedores_estan_ocupados_se_lanza_PoolBusyError():
    async def prueba(pool):
        await pool.get_container()
        await pool.get_container()
        with pytest.raises(PoolBusyError):
            await pool.get_container(timeout=1)
    _run(_con_pool(prueba))


def test_un_contenedor_caido_se_detecta_y_se_recrea():
    async def prueba(pool):
        victima = pool.containers[0]
        await _docker("rm", "-f", victima)
        obtenidos = [await pool.get_container(timeout=20) for _ in range(2)]
        for c in obtenidos:
            code, out = await _docker("inspect", "-f", "{{.State.Running}}", c)
            assert out == "true"
        assert victima in obtenidos
    _run(_con_pool(prueba))
