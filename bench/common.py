"""Utilidades comunes del banco de pruebas: temporizador, CSV con metadatos y percentiles."""
import csv
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.environ.get("BENCH_BACKEND", os.path.join(os.path.dirname(BENCH_DIR), "backend"))
ENTORNO = os.environ.get("BENCH_ENTORNO", "portatil")
RESULTADOS = os.path.join(BENCH_DIR, "resultados", ENTORNO)

# Mismas banderas que services/warm_pool.py::_create en v1.0-paper-baseline
IMAGEN = "tutor-ugr-image:latest"
BANDERAS_POOL = [
    "--network", "none", "--memory", "256m", "--memory-swap", "256m",
    "--cpus", "0.5", "--pids-limit", "64", "--cap-drop", "ALL",
]


def banderas_seguridad() -> list:
    if os.getenv("SANDBOX_NO_NEW_PRIVILEGES", "1") == "0":
        return []
    return ["--security-opt", "no-new-privileges"]


def usar_backend(prefijo: str = "bench_warm_", tam: int = 3) -> None:
    """Deja importable el backend con un pool propio, para no tocar los contenedores de producción."""
    os.environ["WARM_POOL_PREFIX"] = prefijo
    os.environ.setdefault("TERMINAL_PREFIX", "bench_term_")  # el arranque borra las terminales huérfanas de su prefijo
    os.environ["WARM_POOL_SIZE"] = str(tam)
    os.environ.setdefault("TUTOR_MCP_EAGER", "0")
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)


def _cmd(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _cpu() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for linea in f:
                if linea.startswith("model name"):
                    return linea.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def _ram_gib() -> str:
    try:
        with open("/proc/meminfo") as f:
            kb = int(f.readline().split()[1])
        return f"{kb / 1048576:.1f}"
    except Exception:
        return ""


def metadatos(extra: dict = None) -> dict:
    commit = os.environ.get("BENCH_COMMIT") or _cmd("git", "-C", BACKEND_DIR, "rev-parse", "HEAD")
    meta = {
        "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entorno": ENTORNO,
        "commit": commit,
        "cpu": _cpu(),
        "vcpu": str(os.cpu_count()),
        "ram_gib": _ram_gib(),
        "kernel": platform.release(),
        "docker": _cmd("docker", "version", "--format", "{{.Server.Version}}"),
        "python": platform.python_version(),
    }
    meta.update(extra or {})
    return meta


class Csv:
    """CSV con una fila por medida. La cabecera lleva los metadatos en líneas `# clave: valor`.

    Si el archivo ya existe se añade al final: así un script cortado por cuota se puede reanudar.
    """

    def __init__(self, nombre: str, campos: list, extra: dict = None, reanudar: bool = False):
        os.makedirs(RESULTADOS, exist_ok=True)
        self.ruta = os.path.join(RESULTADOS, nombre + ".csv")
        self.campos = campos
        existe = os.path.exists(self.ruta)
        if existe and not reanudar:
            os.replace(self.ruta, self.ruta + ".anterior")
            existe = False
        self._f = open(self.ruta, "a", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._f, fieldnames=campos, extrasaction="ignore")
        if not existe:
            for k, v in metadatos(extra).items():
                self._f.write(f"# {k}: {v}\n")
            self._w.writeheader()
        self._f.flush()

    def fila(self, **valores) -> None:
        self._w.writerow(valores)
        self._f.flush()

    def cerrar(self) -> None:
        self._f.close()


def leer_csv(ruta: str):
    """Devuelve (metadatos, filas)."""
    meta, lineas = {}, []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("# "):
                k, _, v = linea[2:].partition(":")
                meta[k.strip()] = v.strip()
            else:
                lineas.append(linea)
    return meta, list(csv.DictReader(lineas))


def hechas(nombre: str, *claves: str) -> set:
    """Claves ya medidas en un CSV reanudable."""
    ruta = os.path.join(RESULTADOS, nombre + ".csv")
    if not os.path.exists(ruta):
        return set()
    _, filas = leer_csv(ruta)
    return {tuple(f[c] for c in claves) for f in filas}


def percentil(valores: list, p: float) -> float:
    """Percentil con interpolación lineal (el método por defecto de numpy)."""
    v = sorted(valores)
    if not v:
        return float("nan")
    k = (len(v) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def resumen(valores: list) -> dict:
    v = [float(x) for x in valores]
    if not v:
        return {"n": 0}
    return {
        "n": len(v),
        "mediana": statistics.median(v),
        "p95": percentil(v, 95),
        "p99": percentil(v, 99),
        "media": statistics.fmean(v),
        "desv": statistics.stdev(v) if len(v) > 1 else 0.0,
        "min": min(v),
        "max": max(v),
    }


def wilson(exitos: int, n: int, z: float = 1.96):
    """Intervalo de confianza de Wilson al 95 % para una proporción."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = exitos / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - mitad), min(1.0, centro + mitad))


class Crono:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.s = time.perf_counter() - self.t0
        self.ms = self.s * 1000
