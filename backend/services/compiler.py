import asyncio
import shlex
import tempfile
import os
import uuid
from typing import Optional, Tuple
from services.warm_pool import pool, PoolBusyError

# dir local para esquivar snap
LOCAL_TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_workspaces")
os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

EXEC_TIMEOUT_S = 60
MAX_OUTPUT_BYTES = 64 * 1024
COMPILE_ERROR_EXIT = 217  # código reservado: la compilación falló (el programa del alumno no llegó a ejecutarse)


class DockerCommandError(Exception):
    def __init__(self, stderr: str):
        super().__init__(stderr)
        self.stderr = stderr


async def _run(*args: str, timeout: Optional[float] = None, max_output: int = MAX_OUTPUT_BYTES) -> Tuple[int, str, str, bool]:
    """Ejecuta un comando sin bloquear el event loop.

    Devuelve (código, stdout, stderr, truncado). Si el comando escribe más de `max_output` bytes por una
    salida (un `while(1) printf`), se corta y se mata el proceso para no llenar la memoria de la API.
    """
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    async def leer(stream) -> Tuple[bytes, bool]:
        data = bytearray()
        while len(data) <= max_output:
            chunk = await stream.read(65536)
            if not chunk:
                return bytes(data), False
            data += chunk
        if proc.returncode is None:
            proc.kill()
        return bytes(data[:max_output]), True

    try:
        (out, out_cortado), (err, err_cortado) = await asyncio.wait_for(
            asyncio.gather(leer(proc.stdout), leer(proc.stderr)), timeout=timeout
        )
        await proc.wait()
    except BaseException:
        # Timeout o cancelación del cliente: matar el cliente docker y recogerlo
        if proc.returncode is None:
            proc.kill()
        await asyncio.shield(proc.wait())
        raise
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"), out_cortado or err_cortado


async def _run_checked(*args: str) -> None:
    code, _, stderr, _ = await _run(*args)
    if code != 0:
        raise DockerCommandError(stderr)


def _write_project(temp_dir: str, archivos: dict) -> bool:
    """Vuelca los archivos al directorio temporal. Devuelve True si hay un Makefile.

    Rechaza rutas absolutas o que se salgan del directorio (`../../x`): el nombre lo manda el cliente.
    """
    base = os.path.realpath(temp_dir)
    usa_makefile = False
    for nombre, contenido in archivos.items():
        ruta = os.path.realpath(os.path.join(base, nombre))
        if os.path.isabs(nombre) or not ruta.startswith(base + os.sep):
            raise ValueError(f"Ruta no permitida: {nombre}")
        if nombre.lower() == "makefile":
            usa_makefile = True
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
    return usa_makefile


def _build_script(archivos: dict, usa_makefile: bool) -> Optional[str]:
    """Compila y ejecuta en un solo `docker exec`. Si falla la compilación vuelca el log y sale con 217."""
    fallo = f"{{ cat compile_log.txt >&2; exit {COMPILE_ERROR_EXIT}; }}"
    if usa_makefile:
        return (
            f"make > compile_log.txt 2>&1 || {fallo}; "
            "if [ -f ./main ]; then timeout 30 ./main; "
            "elif [ -f ./dist/main ]; then timeout 30 ./dist/main; "
            "elif [ -f ./bin/main ]; then timeout 30 ./bin/main; "
            "else echo ' Error: Ejecutable no encontrado.' >&2; exit 1; fi"
        )
    fuentes = " ".join(shlex.quote(f) for f in archivos if f.endswith((".cpp", ".c")))
    if not fuentes:
        return None
    return f"g++ {fuentes} -I. -o programa.out > compile_log.txt 2>&1 || {fallo}; timeout 30 ./programa.out"


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
            try:
                usa_makefile = await asyncio.to_thread(_write_project, temp_dir, archivos)
            except ValueError as e:
                return {"output": f" Error: {e}", "isError": True}

            script_interno = _build_script(archivos, usa_makefile)
            if script_interno is None:
                return {"output": "Error: No hay archivos .cpp", "isError": True}

            try:
                await _run_checked("docker", "exec", container_name, "mkdir", "-p", container_workdir)
                await _run_checked("docker", "cp", f"{temp_dir}/.", f"{container_name}:{container_workdir}/")

                code, stdout, stderr, cortado = await _run(
                    "docker", "exec", "-w", container_workdir, container_name, "bash", "-c", script_interno,
                    timeout=EXEC_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                return {
                    "output": f" Error: tiempo de ejecución agotado ({EXEC_TIMEOUT_S}s).",
                    "isError": True,
                }
            except DockerCommandError as e:
                return {"output": f" Error interno Docker:\n{e.stderr}", "isError": True}
            except Exception as e:
                return {"output": f"Error de sistema: {str(e)}", "isError": True}

            salida = (stdout + stderr).strip()
            if cortado:
                return {
                    "output": f"{salida}\n[Salida cortada: el programa escribió más de {MAX_OUTPUT_BYTES // 1024} KB]",
                    "isError": True,
                }
            if code == COMPILE_ERROR_EXIT:
                return {"output": f" Error:\n{stderr}", "isError": True}
            if code != 0:
                # Fallo en ejecución: lo que imprimió el programa y por qué terminó
                cuerpo = f"{salida}\n" if salida else ""
                return {"output": f" Error:\n{cuerpo}{_explain_exit_code(code)}", "isError": True}
            return {"output": salida or "[Éxito]", "isError": False}
    finally:
        # El contenedor se recrea en segundo plano: el siguiente alumno recibe uno limpio
        pool.release(container_name)
