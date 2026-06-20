import asyncio
import subprocess

class WarmPoolManager:
    def __init__(self, pool_size=3):
        self.pool_size = pool_size
        self.queue = None 
        self.containers = [f"tutor_warm_{i}" for i in range(pool_size)]

    async def start_pool(self):
        print(f" Iniciando Warm Pool con {self.pool_size} contenedores...")
        self.queue = asyncio.Queue()
        
        for name in self.containers:
            # parar si existe
            subprocess.run(["docker", "stop", name], capture_output=True)
            
            # lanzar limpio
            cmd = [
                "docker", "run", "-d", "--rm",
                "--name", name,
                "tutor-ugr-image:latest",              
                "sleep", "infinity" 
            ]
            subprocess.run(cmd, check=True)
            await self.queue.put(name)
        
        # pausa
        await asyncio.sleep(1.5)
        print(" Warm Pool listo.")

    async def stop_pool(self):
        print(" Deteniendo Warm Pool...")
        for name in self.containers:
            subprocess.run(["docker", "stop", name], capture_output=True)
            
        if self.queue:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def get_container(self):
        if self.queue is None:
            raise RuntimeError("Pool no inicializado.")
        return await self.queue.get()

    def return_container(self, name):
        if self.queue is not None:
            self.queue.put_nowait(name)

pool = WarmPoolManager(pool_size=3)