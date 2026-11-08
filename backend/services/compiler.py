import asyncio
import tempfile
import os
import uuid
from typing import Optional, Tuple
from services.warm_pool import pool, PoolBusyError

# dir local para esquivar snap
LOCAL_TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_workspaces")
os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

EXEC_TIMEOUT_S = 60


class DockerCommandError(Exception):
    def __init__(self, stderr: str):
        super().__init__(stderr)
        self.stderr = stderr


async def _run(*args: str, timeout: Optional[float] = None) -> Tuple[int, str, str]:
    """Ejecuta un comando sin bloquear el event loop. Mata el proceso si vence el timeout."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except BaseException:
        # Timeout o cancelación del cliente: matar el cliente docker y recogerlo
        if proc.returncode is None:
            proc.kill()
        await asyncio.shield(proc.wait())
        raise
    return proc.returncode, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")


async def _run_checked(*args: str) -> None:
    code, _, stderr = await _run(*args)
    if code != 0:
        raise DockerCommandError(stderr)


def _write_project(temp_dir: str, archivos: dict) -> bool:
    """Vuelca los archivos al directorio temporal. Devuelve True si hay un Makefile."""
    usa_makefile = False
    for nombre, contenido in archivos.items():
        if nombre.lower() == "makefile":
            usa_makefile = True
        ruta = os.path.join(temp_dir, nombre)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
    return usa_makefile


def _build_script(archivos: dict, usa_makefile: bool) -> Optional[str]:
    if usa_makefile:
        return (
            "make > compile_log.txt 2>&1 && "
            "if [ -f ./main ]; then timeout 30 ./main; "
            "elif [ -f ./dist/main ]; then timeout 30 ./dist/main; "
            "elif [ -f ./bin/main ]; then timeout 30 ./bin/main; "
            "else echo ' Error: Ejecutable no encontrado.'; exit 1; fi"
        )
    fuentes = " ".join(f for f in archivos.keys() if f.endswith((".cpp", ".c")))
    if not fuentes:
        return None
    return f"g++ {fuentes} -I. -o programa.out > compile_log.txt 2>&1 && timeout 30 ./programa.out"


def _explain_exit_code(code: int) -> str:
    """Salidas sin texto: el kernel o `timeout` mataron el proceso del alumno."""
    if code == 124:
        return "El programa superó el tiempo máximo de ejecución (30 s). ¿Hay un bucle infinito?"
    if code == 137:
        return "El programa fue terminado por el sistema (límite de memoria de 256 MB o de procesos superado)."
    return f"El programa terminó con código de salida {code}."


async def compile_and_run_project(archivos: dict) -> dict:
    try:
        container_name = await pool.get_container()
    except PoolBusyError:
        return {
            "output": " El servidor está ocupado compilando otros proyectos. Inténtalo de nuevo en unos segundos.",
            "isError": True,
        }
    container_workdir = f"/tmp/{uuid.uuid4()}"

    try:
        with tempfile.TemporaryDirectory(dir=LOCAL_TEMP_DIR) as temp_dir:
            usa_makefile = await asyncio.to_thread(_write_project, temp_dir, archivos)

            script_interno = _build_script(archivos, usa_makefile)
            if script_interno is None:
                return {"output": "Error: No hay archivos .cpp", "isError": True}

            try:
                await _run_checked("docker", "exec", container_name, "mkdir", "-p", container_workdir)
                await _run_checked("docker", "cp", f"{temp_dir}/.", f"{container_name}:{container_workdir}/")

                code, stdout, stderr = await _run(
                    "docker", "exec", "-w", container_workdir, container_name, "bash", "-c", script_interno,
                    timeout=EXEC_TIMEOUT_S,
                )

                if code != 0:
                    _, log, _ = await _run(
                        "docker", "exec", "-w", container_workdir, container_name, "cat", "compile_log.txt"
                    )
                    detalle = log or stderr or _explain_exit_code(code)
                    return {"output": f" Error:\n{detalle}", "isError": True}

                return {"output": stdout if stdout else "[Éxito]", "isError": False}

            except asyncio.TimeoutError:
                return {
                    "output": f" Error: tiempo de ejecución agotado ({EXEC_TIMEOUT_S}s).",
                    "isError": True,
                }
            except DockerCommandError as e:
                return {"output": f" Error interno Docker:\n{e.stderr}", "isError": True}
            except Exception as e:
                return {"output": f"Error de sistema: {str(e)}", "isError": True}
    finally:
        # El contenedor se recrea en segundo plano: el siguiente alumno recibe uno limpio
        pool.release(container_name)
