"""Paso 2.5.4 y 2.5.8: muestreo de la máquina servidora durante la carga (se ejecuta en la VM).

Cada 2 s: CPU de la máquina, memoria disponible, carga media, contenedores vivos por prefijo y memoria
residente del proceso de la API de pruebas.
Uso: python bench/carga/monitor.py --etiqueta carga [--segundos 3600]
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c


def cpu():
    with open("/proc/stat") as f:
        v = [int(x) for x in f.readline().split()[1:8]]
    return sum(v), v[3] + v[4]


def mem_disp_mb() -> int:
    with open("/proc/meminfo") as f:
        for l in f:
            if l.startswith("MemAvailable"):
                return int(l.split()[1]) // 1024
    return 0


def rss_api_mb() -> int:
    r = subprocess.run(["pgrep", "-f", "servidor_mock.py"], capture_output=True, text=True)
    total = 0
    for pid in r.stdout.split():
        try:
            with open(f"/proc/{pid}/statm") as f:
                total += int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        except OSError:
            pass
    return total // 1048576


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="carga")
    ap.add_argument("--segundos", type=int, default=3600)
    a = ap.parse_args()
    out = c.Csv(f"monitor_{a.etiqueta}", ["epoch_s", "cpu_pct", "mem_disp_mb", "carga_1m", "contenedores_bench",
                                           "contenedores_total", "rss_api_mb"], {"periodo_s": 2})
    t0, i0 = cpu()
    fin = time.time() + a.segundos
    while time.time() < fin:
        time.sleep(2)
        t1, i1 = cpu()
        nombres = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
        out.fila(epoch_s=round(time.time(), 1), cpu_pct=round(100 * (1 - (i1 - i0) / max(1, t1 - t0)), 1),
                 mem_disp_mb=mem_disp_mb(), carga_1m=os.getloadavg()[0],
                 contenedores_bench=sum(n.startswith("bench_") for n in nombres), contenedores_total=len(nombres),
                 rss_api_mb=rss_api_mb())
        t0, i0 = t1, i1
