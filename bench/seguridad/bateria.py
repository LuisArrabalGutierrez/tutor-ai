"""Pasos 2.4.2, 2.4.3 y 2.4.6: batería de ataques contra el Warm Pool.

Cada ataque pasa por `compile_and_run_project`, el mismo camino que `/api/execute`. Mientras corre,
un hilo muestrea la máquina anfitriona (CPU, memoria libre, procesos) y `docker stats` del pool.
Uso: python bench/seguridad/bateria.py [--n 10] [--solo ataque]
"""
import argparse
import asyncio
import os
import re
import secrets
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

c.usar_backend()
from services import compiler  # noqa: E402
from services.warm_pool import pool  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
ATAQUES = os.path.join(AQUI, "ataques")
CANARIO = os.path.join(AQUI, "canario_host.txt")
MB_DISCO_TOPE = 1024
SIN_RESPUESTA_S = 150  # EXEC_TIMEOUT_S es 60: pasado este margen la petición se da por colgada


class Muestreo(threading.Thread):
    """Picos de la máquina y de los contenedores del pool durante un ataque."""

    def __init__(self):
        super().__init__(daemon=True)
        self.parar = threading.Event()
        self.cpu_host_max = 0.0
        self.mem_disp_min_mb = float("inf")
        self.procs_host_max = 0
        self.cont_mem_max_mb = 0.0
        self.cont_cpu_max = 0.0
        self.cont_pids_max = 0

    @staticmethod
    def _cpu():
        with open("/proc/stat") as f:
            v = [int(x) for x in f.readline().split()[1:8]]
        return sum(v), v[3] + v[4]

    @staticmethod
    def _mem_disp_mb() -> float:
        with open("/proc/meminfo") as f:
            for l in f:
                if l.startswith("MemAvailable"):
                    return int(l.split()[1]) / 1024
        return 0.0

    def _stats(self) -> None:
        r = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.PIDs}}"],
                           capture_output=True, text=True)
        for l in r.stdout.splitlines():
            if not l.startswith("bench_warm_"):
                continue
            p = l.split()
            try:
                self.cont_cpu_max = max(self.cont_cpu_max, float(p[1].rstrip("%")))
                m = re.match(r"([\d.]+)(\w+)", p[2])
                factor = {"B": 1 / 1048576, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024}.get(m.group(2), 0)
                self.cont_mem_max_mb = max(self.cont_mem_max_mb, float(m.group(1)) * factor)
                self.cont_pids_max = max(self.cont_pids_max, int(p[-1]))
            except (ValueError, AttributeError, IndexError):
                pass

    def run(self) -> None:
        total0, idle0 = self._cpu()
        while not self.parar.is_set():
            self._stats()  # tarda 1-2 s: marca el periodo de muestreo
            total1, idle1 = self._cpu()
            if total1 > total0:
                self.cpu_host_max = max(self.cpu_host_max, 100 * (1 - (idle1 - idle0) / (total1 - total0)))
            total0, idle0 = total1, idle1
            self.mem_disp_min_mb = min(self.mem_disp_min_mb, self._mem_disp_mb())
            self.procs_host_max = max(self.procs_host_max, sum(1 for d in os.listdir("/proc") if d.isdigit()))
            self.parar.wait(0.3)


def _ultimo(patron: str, texto: str, defecto: int = 0) -> int:
    m = re.findall(patron, texto)
    return int(m[-1]) if m else defecto


# Cada veredicto devuelve (contenido, evidencia). `s` es la salida, `m` el muestreo, `x` datos extra.
def v_fork(s, m, x):
    return m.cont_pids_max <= 64 and x["ms"] < 61000, f"pids_max={m.cont_pids_max}"


def v_memoria(s, m, x):
    mb = _ultimo(r"MB=(\d+)", s)
    return "SIN_LIMITE" not in s and mb <= 256, f"mb_reservados={mb}"


def v_cpu(s, m, x):
    return "tiempo máximo" in s and m.cont_cpu_max <= 75, f"cpu_contenedor_max={m.cont_cpu_max:.0f}%"


def v_red(s, m, x):
    return "CONEXION_OK" not in s and "DNS_OK" not in s, ("conexion y DNS fallan" if "CONEXION_FALLA" in s else s[:60])


def v_disco(s, m, x):
    mb = _ultimo(r"MB=(\d+)", s)
    return "SIN_LIMITE" not in s and mb < MB_DISCO_TOPE, f"mb_escritos={max(mb, MB_DISCO_TOPE if 'SIN_LIMITE' in s else 0)}"


def v_host(s, m, x):
    leidos = sum(1 for l in s.splitlines() if l.startswith("LEIDO "))
    return x["token"] not in s and leidos == 0, f"archivos_leidos={leidos}"


def v_proc(s, m, x):
    pids = _ultimo(r"PIDS_VISIBLES=(\d+)", s, 9999)
    mem, nuc = _ultimo(r"MEMTOTAL_KB=(\d+)", s), _ultimo(r"NUCLEOS=(\d+)", s)
    return pids < 20, f"pids_visibles={pids} memtotal_kb={mem} nucleos={nuc}"


def v_otro(s, m, x):
    senales = _ultimo(r"SENALES_ACEPTADAS=(\d+)", s)
    return x["otros_vivos"], f"otros_contenedores_intactos={x['otros_vivos']} senales={senales}"


def v_salida(s, m, x):
    return "Salida cortada" in s and len(s) < 80000, f"bytes_devueltos={len(s)}"


CATALOGO = [
    # nombre, archivo, mecanismo esperado, veredicto
    ("bomba_fork", "fork_bomb.cpp", "--pids-limit 64 y timeout", v_fork),
    ("memoria", "memoria.cpp", "--memory 256m sin swap (OOM killer)", v_memoria),
    ("cpu", "cpu.cpp", "--cpus 0.5 y timeout 30 s", v_cpu),
    ("red", "red.cpp", "--network none", v_red),
    ("disco_tmp", "disco_tmp.cpp", "ninguno previsto", v_disco),
    ("disco_cwd", "disco_cwd.cpp", "ninguno previsto", v_disco),
    ("leer_host", "leer_host.cpp", "sistema de archivos propio y usuario sin privilegios", v_host),
    ("proc", "proc.cpp", "espacio de nombres de PID", v_proc),
    ("otro_contenedor", "otro_contenedor.cpp", "espacio de nombres de PID", v_otro),
    ("salida", "salida.cpp", "tope de 64 KB en la API", v_salida),
]


def ids() -> dict:
    r = subprocess.run(["docker", "ps", "--no-trunc", "--filter", "name=bench_warm_", "--format", "{{.Names}} {{.ID}}"],
                       capture_output=True, text=True)
    return dict(l.split() for l in r.stdout.splitlines() if l.strip())


async def _libre() -> None:
    while pool._recycling:
        await asyncio.gather(*list(pool._recycling.values()), return_exceptions=True)


async def main(n: int, solo: str) -> None:
    token = secrets.token_hex(16)
    with open(CANARIO, "w") as f:
        f.write(f"CANARIO-{token}\n")
    out = c.Csv("seguridad_bateria",
                ["ataque", "rep", "contenido", "mecanismo", "evidencia", "ms", "cpu_host_max", "mem_host_caida_mb",
                 "procs_host_delta", "cont_mem_max_mb", "cont_cpu_max", "cont_pids_max", "salida"],
                {"objetivo": "warm pool (compile_and_run_project)"}, reanudar=bool(solo))
    await pool.start_pool()
    try:
        for nombre, archivo, mecanismo, veredicto in CATALOGO:
            if solo and nombre != solo:
                continue
            with open(os.path.join(ATAQUES, archivo), encoding="utf-8") as f:
                archivos = {"main.cpp": f.read()}
            if nombre == "leer_host":
                archivos["canario.txt"] = CANARIO + "\n"
            for rep in range(n):
                mem0 = Muestreo._mem_disp_mb()
                procs0 = sum(1 for d in os.listdir("/proc") if d.isdigit())
                antes = ids()
                m = Muestreo()
                m.start()
                with c.Crono() as t:
                    tarea = asyncio.create_task(compiler.compile_and_run_project(archivos))
                    hechas, _ = await asyncio.wait([tarea], timeout=SIN_RESPUESTA_S)
                m.parar.set()
                m.join()
                if not hechas:
                    # La API no contestó: se anota como no contenido y se rehace el pool para seguir
                    out.fila(ataque=nombre, rep=rep, contenido=0, mecanismo=mecanismo,
                             evidencia=f"sin respuesta en {SIN_RESPUESTA_S} s", ms=round(t.ms),
                             cpu_host_max=round(m.cpu_host_max, 1), cont_mem_max_mb=round(m.cont_mem_max_mb, 1),
                             cont_cpu_max=round(m.cont_cpu_max, 1), cont_pids_max=m.cont_pids_max, salida="")
                    print(f"{nombre} rep {rep}: SIN RESPUESTA", flush=True)
                    await pool.stop_pool()
                    await pool.start_pool()
                    continue
                res = tarea.result()
                despues_inmediato = ids()
                # El contenedor usado se recrea; los otros dos deben seguir con el mismo ID
                intactos = sum(1 for k, v in antes.items() if despues_inmediato.get(k) == v)
                await _libre()
                x = {"ms": t.ms, "token": token, "otros_vivos": intactos >= len(antes) - 1 and len(ids()) == len(antes)}
                contenido, evidencia = veredicto(res["output"], m, x)
                out.fila(ataque=nombre, rep=rep, contenido=int(contenido), mecanismo=mecanismo, evidencia=evidencia,
                         ms=round(t.ms), cpu_host_max=round(m.cpu_host_max, 1),
                         mem_host_caida_mb=round(max(0.0, mem0 - m.mem_disp_min_mb)),
                         procs_host_delta=max(0, m.procs_host_max - procs0),
                         cont_mem_max_mb=round(m.cont_mem_max_mb, 1), cont_cpu_max=round(m.cont_cpu_max, 1),
                         cont_pids_max=m.cont_pids_max,
                         salida=res["output"][-160:].replace("\n", " | ").replace(token, "<TOKEN>"))
                print(f"{nombre} rep {rep}: {'CONTENIDO' if contenido else 'NO CONTENIDO'} ({evidencia})", flush=True)
    finally:
        await pool.stop_pool()
        out.cerrar()
        os.remove(CANARIO)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--solo", default="")
    a = ap.parse_args()
    asyncio.run(main(a.n, a.solo))
