import asyncio
import os
import sys
from typing import Dict, List, Optional

IMAGE = "tutor-ugr-image:latest"
ACQUIRE_TIMEOUT_S = 30
RECYCLE_RETRIES = 3
RECYCLE_RETRY_DELAY_S = 2


class PoolBusyError(Exception):
    """Todos los contenedores están ocupados y no se liberó ninguno a tiempo."""


def _log(msg: str) -> None:
    # stderr: el servidor MCP usa stdout para el protocolo, no se puede imprimir ahí
    print(msg, file=sys.stderr, flush=True)


async def _docker(*args: str, timeout: Optional[float] = None) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "docker", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
        await asyncio.shield(proc.wait())
        raise
    return proc.returncode, out.decode("utf-8", "replace").strip()


class WarmPoolManager:
    """Contenedores precalentados para compilar. Cada uso termina con la recreación del contenedor,
    así un alumno nunca hereda procesos ni archivos de otro."""

    def __init__(self, pool_size: int = 3, prefix: str = "tutor_warm_"):
        self.pool_size = pool_size
        self.prefix = prefix
        self.queue: Optional[asyncio.Queue] = None
        self.containers: List[str] = [f"{prefix}{i}" for i in range(pool_size)]
        self._recycling: Dict[str, asyncio.Task] = {}

    async def _create(self, name: str) -> None:
        # Forzar eliminación de cualquier contenedor huérfano con el mismo nombre
        await _docker("rm", "-f", name)
        code, out = await _docker(
            "run", "-d", "--rm",
            "--name", name,
            "--network", "none",
            "--memory", "256m",
            "--memory-swap", "256m",
            "--cpus", "0.5",
            "--pids-limit", "64",
            # no-new-privileges se probó y en este host Docker hace fallar el exec de `sleep` (operation not permitted)
            "--cap-drop", "ALL",
            IMAGE,
            "sleep", "infinity",
        )
        if code != 0:
            raise RuntimeError(f"No se pudo crear {name}: {out}")

    async def start_pool(self) -> None:
        _log(f" Iniciando Warm Pool '{self.prefix}*' con {self.pool_size} contenedores...")
        self.queue = asyncio.Queue()
        for name in self.containers:
            await self._create(name)
            await self.queue.put(name)
        # Pausa para estabilizar
        await asyncio.sleep(1.5)
        _log(f" Warm Pool '{self.prefix}*' listo.")

    async def stop_pool(self) -> None:
        _log(f" Deteniendo Warm Pool '{self.prefix}*'...")
        for task in list(self._recycling.values()):
            task.cancel()
        self._recycling.clear()
        for name in self.containers:
            await _docker("rm", "-f", name)
        if self.queue:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def _is_running(self, name: str) -> bool:
        try:
            code, out = await _docker("inspect", "-f", "{{.State.Running}}", name, timeout=5)
        except Exception:
            return False
        return code == 0 and out == "true"

    async def get_container(self, timeout: float = ACQUIRE_TIMEOUT_S) -> str:
        """Devuelve un contenedor sano. Lanza PoolBusyError si no hay ninguno libre a tiempo."""
        if self.queue is None:
            raise RuntimeError("Pool no inicializado.")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            restante = deadline - loop.time()
            if restante <= 0:
                raise PoolBusyError("Todos los contenedores de compilación están ocupados.")
            try:
                name = await asyncio.wait_for(self.queue.get(), timeout=restante)
            except asyncio.TimeoutError:
                raise PoolBusyError("Todos los contenedores de compilación están ocupados.") from None
            if await self._is_running(name):
                return name
            _log(f" Contenedor {name} caído; se recrea.")
            self._schedule_recycle(name)

    def release(self, name: str) -> None:
        """Devuelve el contenedor al pool recreándolo en segundo plano (estado limpio para el siguiente alumno)."""
        if self.queue is not None:
            self._schedule_recycle(name)

    def _schedule_recycle(self, name: str) -> None:
        if name in self._recycling:
            return
        task = asyncio.create_task(self._recycle(name))
        self._recycling[name] = task
        task.add_done_callback(lambda _t, n=name: self._recycling.pop(n, None))

    async def _recycle(self, name: str) -> None:
        for intento in range(1, RECYCLE_RETRIES + 1):
            try:
                await self._create(name)
                if self.queue is not None:
                    self.queue.put_nowait(name)
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                _log(f" Recreando {name} (intento {intento}/{RECYCLE_RETRIES}): {e}")
                await asyncio.sleep(RECYCLE_RETRY_DELAY_S)
        _log(f" {name} no se pudo recrear; el pool queda con un contenedor menos.")


pool = WarmPoolManager(
    pool_size=int(os.getenv("WARM_POOL_SIZE", "3")),
    prefix=os.getenv("WARM_POOL_PREFIX", "tutor_warm_"),
)
