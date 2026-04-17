import asyncio
import os
import pty
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    await websocket.accept()
    
    # Creamos una Pseudo-Terminal (PTY) de Linux
    master_fd, slave_fd = pty.openpty()

    # Hijo del proceso para lanzar Bash
    pid = os.fork()
    if pid == 0:

        # --- PROCESO HIJO (El Bash Real) ---
        os.setsid()
        os.dup2(slave_fd, 0) # Conectar Entrada
        os.dup2(slave_fd, 1) # Conectar Salida
        os.dup2(slave_fd, 2) # Conectar Errores
        
        if master_fd > 2: os.close(master_fd)
        if slave_fd > 2: os.close(slave_fd)
        
        # bash interactivo para trabajar con las ordenes
        # docker run: lanza un contenedor
        # -it: modo interactivo con terminal (para que xterm.js pille colores y teclas)
        # --rm: destruye el contenedor automáticamente cuando el alumno sale
        # ubuntu: la imagen base (se puede cambiar por debian, alpine, etc.)
        # bash: el programa a ejecutar
        os.execvp("docker", ["docker", "run", "-it", "--rm", "tutor-ugr-image", "bash"])
    # --- PROCESO PADRE (FastAPI) ---
    os.close(slave_fd)

    # Tarea para LEER del Bash y mandarlo a React
    async def read_from_pty():
        loop = asyncio.get_running_loop()
        try:
            while True:
                # Leemos lo que dice Linux
                data = await loop.run_in_executor(None, os.read, master_fd, 4096)
                if not data: 
                    break
                # Lo mandamos por el WebSocket
                await websocket.send_text(data.decode("utf-8", "replace"))
        except Exception:
            pass


    # Tarea para ESCUCHAR a React y meterlo en Bash
    async def write_to_pty():
        try:
            while True:
                data = await websocket.receive_text()
                # Escribimos las teclas del alumno en Linux
                os.write(master_fd, data.encode("utf-8"))
        except WebSocketDisconnect:

            pass


    # Ejecutamos ambas tareas a la vez
    task1 = asyncio.create_task(read_from_pty())
    task2 = asyncio.create_task(write_to_pty())

    # Esperamos a que el alumno cierre la pestaña o escriba 'exit'
    done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
    for task in pending: 
        task.cancel()
    
    os.close(master_fd)