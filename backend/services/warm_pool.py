import asyncio
import subprocess

class WarmPoolManager:
    def __init__(self, pool_size=3):
        self.pool_size = pool_size
        self.queue = None 
        self.containers = [f"tutor_warm_{i}" for i in range(pool_size)]

    async def start_pool(self):
        print(f"🚀 Iniciando Warm Pool con {self.pool_size} contenedores...")
        # Inicializamos la cola aquí para que use el loop de la app actual
        self.queue = asyncio.Queue()
        
        for name in self.containers:
            # Limpieza preventiva
            subprocess.run(["docker", "stop", name], capture_output=True)
            
            cmd = [
                "docker", "run", "-d", "--rm",
                "--name", name,
                "--network", "none",       
                "--memory", "256m",
                "--memory-swap", "256m",               
                "--cpus", "0.5",           
                "--pids-limit", "64",                  
                "--security-opt", "no-new-privileges", 
                "--cap-drop", "ALL",                   
                "tutor-ugr-image:latest",              
                "tail", "-f", "/dev/null" 
            ]
            subprocess.run(cmd, check=True)
            await self.queue.put(name)
        
        # Tiempo de gracia para que Docker estabilice el sistema de archivos
        await asyncio.sleep(1.5)
        print("✅ Warm Pool listo.")

    async def stop_pool(self):
        print("🛑 Deteniendo Warm Pool...")
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
            raise RuntimeError("El pool no está inicializado.")
        return await self.queue.get()

    def return_container(self, name):
        if self.queue is not None:
            self.queue.put_nowait(name)

pool = WarmPoolManager(pool_size=3)