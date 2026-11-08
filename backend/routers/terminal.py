import asyncio
import os
import pty
import json
import fcntl
import termios
import struct
import signal
import uuid
import subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

router = APIRouter()

# Tope de terminales simultáneas: cada una reserva hasta 512 MB en la VM
MAX_TERMINALS = int(os.getenv("MAX_TERMINALS", "10"))
_active_terminals = 0


@router.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    global _active_terminals
    await websocket.accept()

    if _active_terminals >= MAX_TERMINALS:
        await websocket.send_text(
            "\r\n\x1b[33m[Hay demasiadas terminales abiertas ahora mismo. Inténtalo de nuevo en un minuto.]\x1b[0m\r\n"
        )
        await websocket.close(code=1013)
        return
    _active_terminals += 1

    # Identificador único de contenedor para garantizar aislamiento y cierre limpio
    container_name = f"tutor_term_{uuid.uuid4().hex[:12]}"
    loop = asyncio.get_running_loop()

    # Creamos una Pseudo-Terminal (PTY) de Linux
    master_fd, slave_fd = pty.openpty()

    pid = os.fork()
    if pid == 0:
        # --- PROCESO HIJO (El Bash en Docker) ---
        os.setsid()
        os.dup2(slave_fd, 0)  # Entrada estándar
        os.dup2(slave_fd, 1)  # Salida estándar
        os.dup2(slave_fd, 2)  # Error estándar

        if master_fd > 2:
            os.close(master_fd)
        if slave_fd > 2:
            os.close(slave_fd)

        # Lanzar bash interactivo dentro del sandbox seguro de Docker sin permisos root (UID 1000)
        os.execvp("docker", [
            "docker", "run", "-it", "--rm",
            "--name", container_name,
            "--network", "none",
            "--cap-drop", "ALL",
            "--cpus", "1",
            "--user", "1000:1000",
            "-w", "/home/alumno",
            "-e", "HOME=/home/alumno",
            "--pids-limit", "100",
            "--memory", "512m",
            "tutor-ugr-image", "bash"
        ])

    # --- PROCESO PADRE (FastAPI) ---
    os.close(slave_fd)
    websocket.state.pid = pid

    pty_queue = asyncio.Queue()
    is_reader_registered = False

    def on_pty_readable():
        """Callback no bloqueante ejecutado por el bucle de eventos (epoll)."""
        try:
            data = os.read(master_fd, 4096)
            if not data:
                pty_queue.put_nowait(None)  # EOF
            else:
                pty_queue.put_nowait(data)
        except (OSError, ValueError):
            pty_queue.put_nowait(None)

    try:
        loop.add_reader(master_fd, on_pty_readable)
        is_reader_registered = True
    except Exception as e:
        print(f"⚠️ [Terminal] Error registrando reader en loop: {e}")

    # Tarea para LEER del PTY y mandarlo al frontend por WebSocket
    async def read_from_pty():
        try:
            while True:
                data = await pty_queue.get()
                if data is None:
                    break
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(data.decode("utf-8", "replace"))
        except Exception:
            pass

    # Tarea para ESCUCHAR del WebSocket e inyectarlo en el PTY (con soporte de resize)
    async def write_to_pty():
        try:
            while True:
                data = await websocket.receive_text()

                # Soporte de mensaje de control JSON para redimensión de ventana (TIOCSWINSZ)
                if data.startswith("{") and "resize" in data:
                    try:
                        msg = json.loads(data)
                        if msg.get("type") == "resize":
                            cols = int(msg.get("cols", 80))
                            rows = int(msg.get("rows", 24))
                            winsize = struct.pack("HHHH", rows, cols, 0, 0)
                            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                            continue
                    except Exception:
                        pass

                # Escritura de teclas / comandos del alumno en Linux
                os.write(master_fd, data.encode("utf-8"))
        except (WebSocketDisconnect, Exception):
            pass

    try:
        task1 = asyncio.create_task(read_from_pty())
        task2 = asyncio.create_task(write_to_pty())

        # Esperamos a que el alumno cierre la conexión, escriba 'exit' o se desconecte
        done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()

    finally:
        _active_terminals -= 1

        # 1. Quitar el file descriptor del loop de eventos de forma segura
        if is_reader_registered:
            try:
                loop.remove_reader(master_fd)
            except Exception:
                pass

        # 2. Cerrar master_fd
        try:
            os.close(master_fd)
        except OSError:
            pass

        # 3. Terminar proceso hijo y recolectarlo para EVITAR ZOMBIS (SIGTERM + waitpid)
        child_pid = getattr(websocket.state, "pid", pid)
        if child_pid and child_pid > 0:
            try:
                os.kill(child_pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass

            # Espera no bloqueante breve para dar tiempo al cierre limpio
            try:
                for _ in range(5):
                    rpid, _ = os.waitpid(child_pid, os.WNOHANG)
                    if rpid == child_pid:
                        break
                    await asyncio.sleep(0.05)
                else:
                    # Si no ha cerrado con SIGTERM, forzar SIGKILL y waitpid
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    os.waitpid(child_pid, 0)
            except (ChildProcessError, ProcessLookupError, OSError):
                pass

        # 4. Red de seguridad estricta: destruir contenedor Docker por nombre
        def _force_kill_docker():
            try:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
            except Exception:
                pass

        await asyncio.to_thread(_force_kill_docker)

        # 5. Cerrar websocket si sigue abierto
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception:
                pass
