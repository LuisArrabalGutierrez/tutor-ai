"""Tablas, figuras y cifras a partir de los CSV de resultados/.

Dos salidas con los mismos datos:
- documentación (español): <bench>/tablas.md y <bench>/figuras/*.png
- artículo (inglés): <paper>/figures/*.pdf, <paper>/generated/tab_*.tex y <paper>/generated/numbers.tex
  (una macro LaTeX por cifra, para que ningún número del texto se escriba a mano)

Solo usa lo que ya está medido; si falta un CSV, esa sección se salta.
Uso: venv/bin/python figuras.py [--salida ../docs/bench] [--paper ../docs/paper/latex]
"""
import argparse
import collections
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import common as c  # noqa: E402

RES = os.path.join(c.BENCH_DIR, "resultados")
# Paleta de referencia validada (skill dataviz): azul, naranja, aqua sobre fondo claro
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, FONDO = "#0b0b0b", "#52514e", "#fcfcfb"
ANCHO_COLUMNA_IN = 3.45  # una columna de IEEEtran

BASE = {
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "text.color": TINTA, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e4e3df", "grid.linewidth": 0.8,
    "font.size": 10, "figure.dpi": 150, "axes.axisbelow": True,
}

# Objetivos del registro de decisiones del plan (2026-11-19). "a priori": escritos antes de medir;
# "prerregistrado": fijado antes de medir esa métrica. Los post-hoc no se listan: no cuentan como éxito.
OBJETIVOS = [
    ("reduccion_pool", "Warm Pool: reducción de la mediana frente a frío", "Warm Pool: median reduction vs.\\ cold start", ">= 0.75", "a priori"),
    ("sobrecoste", "Sobrecoste de aislamiento (mediana, peor programa)", "Isolation overhead (median, worst program)", "<= 0.15", "a priori"),
    ("terminacion", "Terminación tras el timeout de 30 s (p95)", "Termination after the 30\\,s timeout (p95)", "<= 500 ms", "a priori"),
    ("contencion", "Tasa de contención", "Containment rate", "= 1.00", "a priori"),
    ("recall3", "RAG Recall@3 (estricto)", "RAG Recall@3 (strict)", ">= 0.88", "a priori"),
    ("ruteo", "Acierto de ruteo (primera herramienta)", "Routing accuracy (first tool)", ">= 0.96", "a priori"),
    ("docs_p95", "p95 de /docs con 10, 50 y 100 clientes", "p95 of \\texttt{/docs} at 10, 50, 100 clients", "<= 1 s", "prerregistrado"),
    ("execute_p95", "p95 de /api/execute con 10 clientes", "p95 of \\texttt{/api/execute} at 10 clients", "<= 10 s", "prerregistrado"),
    ("errores_5xx", "Respuestas 5xx bajo carga", "5xx responses under load", "= 0", "prerregistrado"),
    ("limitador", "Limitador: aceptadas de 60 en 60 s", "Rate limiter: accepted of 60 in 60\\,s", "15 ± 1", "prerregistrado"),
    ("ttft_rapida", "TTFT p95, ruta rápida", "TTFT p95, fast path", "<= 1 s", "prerregistrado"),
    ("ttft_agente", "TTFT p95 con RAG o compilación", "TTFT p95, RAG or compile path", "<= 10 s", "prerregistrado"),
    ("fuga", "Fugas en 40 prompts de ataque x3", "Leaks in 40 attack prompts $\\times$3", "= 0", "prerregistrado"),
    ("legitimos", "Prompts legítimos sin bloquear", "Legitimate prompts not blocked", "10 / 10", "prerregistrado"),
]

ATAQUES_EN = {
    "bomba_fork": ("Fork bomb", "\\texttt{--pids-limit 64}"),
    "memoria": ("Memory exhaustion", "\\texttt{--memory 256m}, no swap (OOM)"),
    "cpu": ("CPU spin", "\\texttt{--cpus 0.5} + 30\\,s timeout"),
    "red": ("Outbound network", "\\texttt{--network none}"),
    "disco_tmp": ("Disk fill (\\texttt{/tmp})", "none configured"),
    "disco_cwd": ("Disk fill (workdir)", "none configured"),
    "leer_host": ("Read host files", "own mount ns, unprivileged user"),
    "proc": ("Inspect \\texttt{/proc}", "PID namespace"),
    "otro_contenedor": ("Reach other container", "PID namespace"),
    "salida": ("Output flooding", "64\\,KB cap in the API"),
}
GRUPOS_EN = {"todas": "All", "FP": "FP", "MP": "MP", "FS": "FS",
             "teoria": "Theory", "codigo": "With code", "erratas": "With typos", "ambigua": "Ambiguous"}
HERRAMIENTAS_EN = {"ninguna": "none", "apuntes": "notes", "compilar": "compile", "internet": "web"}


class Salida:
    """Una pasada de generación: idioma, carpeta, formato de figura y, en inglés, LaTeX y macros."""

    def __init__(self, lang, carpeta):
        self.lang = lang
        self.carpeta = carpeta
        self.es = lang == "es"
        self.figs = os.path.join(carpeta, "figuras" if self.es else "figures")
        self.gen = None if self.es else os.path.join(carpeta, "generated")
        for d in (self.figs, self.gen):
            if d:
                os.makedirs(d, exist_ok=True)
        self.md, self.num, self.cumple = [], {}, {}

    def t(self, es, en):
        return es if self.es else en

    def n(self, x, d=1):
        s = f"{x:,.{d}f}"
        return s.replace(",", " ").replace(".", ",") if self.es else s.replace(",", "\\,")

    def pct(self, p, d=0):
        return f"{p * 100:.{d}f}".replace(".", ",") + " %" if self.es else f"{p * 100:.{d}f}\\%"

    def figura(self, w, h):
        if self.es:
            plt.rcParams.update(BASE)
            return plt.subplots(figsize=(w, h))
        plt.rcParams.update({**BASE, "font.size": 7.5, "figure.dpi": 300})
        return plt.subplots(figsize=(ANCHO_COLUMNA_IN, h * ANCHO_COLUMNA_IN / w * 1.12))

    def titulo(self, ax, es):
        if self.es:  # en el artículo el título va en el caption
            ax.set_title(es, fontsize=10)

    def guardar(self, fig, nombre):
        fig.tight_layout()
        archivo = f"{nombre}.{'png' if self.es else 'pdf'}"
        fig.savefig(os.path.join(self.figs, archivo), bbox_inches="tight")
        plt.close(fig)
        if self.es:
            self.md.append(f"\n![{archivo}](figuras/{archivo})")

    def tabla_md(self, cab, filas):
        if not self.es:
            return
        out = ["| " + " | ".join(cab) + " |", "| " + " | ".join(":---" if i == 0 else "---:" for i in range(len(cab))) + " |"]
        out += ["| " + " | ".join(str(v) for v in f) + " |" for f in filas]
        self.md.append("\n".join(out))

    def texto(self, s):
        if self.es:
            self.md.append(s)

    def latex(self, clave, cab, filas, caption, ancha=False, alin=None):
        if self.es:
            return
        alin = alin or "l" + "r" * (len(cab) - 1)
        entorno = "table*" if ancha else "table"
        cuerpo = [" & ".join(str(v) for v in f) + " \\\\" for f in filas]
        tex = "\n".join([
            f"% Generado por bench/figuras.py: no editar a mano.",
            f"\\begin{{{entorno}}}[t]", "\\centering", "\\footnotesize", "\\setlength{\\tabcolsep}{4pt}",
            f"\\caption{{{caption}}}", f"\\label{{tab:{clave}}}",
            f"\\begin{{tabular}}{{{alin}}}", "\\toprule",
            " & ".join(f"\\textbf{{{h}}}" for h in cab) + " \\\\", "\\midrule",
            *cuerpo, "\\bottomrule", "\\end{tabular}", f"\\end{{{entorno}}}", ""])
        with open(os.path.join(self.gen, f"tab_{clave}.tex"), "w", encoding="utf-8") as f:
            f.write(tex)

    def macro(self, nombre, valor):
        self.num[nombre] = valor

    def fuente(self, meta, entorno, nombre):
        """Línea de origen al final de la sección de la documentación."""
        if self.es:
            cpu = f", {meta['cpu']}" if meta.get("cpu") else ""
            self.md.append(f"\n*Fuente: `resultados/{entorno}/{nombre}.csv`, {meta.get('fecha_utc', '?')}, "
                           f"commit `{meta.get('commit', '?')[:7]}`{cpu}.*\n")

    @staticmethod
    def origen_tex(meta, entorno, nombre):
        """Origen para el caption de una tabla del artículo."""
        nombre = nombre.replace("_", "\\_")
        return f" Source: \\texttt{{{entorno}/{nombre}.csv}}, commit \\texttt{{{meta.get('commit', '?')[:7]}}}."


def cargar(entorno, nombre):
    ruta = os.path.join(RES, entorno, nombre + ".csv")
    return c.leer_csv(ruta) if os.path.exists(ruta) else (None, None)


def validas(filas):
    return [f for f in filas if f.get("calentamiento", "0") == "0"]


def barras_mediana_p95(o, ax, etiquetas, res, color):
    x = range(len(etiquetas))
    ax.bar(x, [r["mediana"] for r in res], width=0.55, color=color, label=o.t("mediana", "median"))
    ax.errorbar(x, [r["mediana"] for r in res],
                yerr=[[0] * len(res), [r["p95"] - r["mediana"] for r in res]],
                fmt="none", ecolor=TINTA2, capsize=4, linewidth=1.2, label=o.t("hasta p95", "to p95"))
    for i, r in enumerate(res):
        ax.annotate(f"{r['mediana']:.0f}", (i, r["p95"]), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9 if o.es else 7, color=TINTA, zorder=5,
                    bbox=dict(boxstyle="square,pad=0.1", facecolor=FONDO, edgecolor="none"))
    ax.set_xticks(list(x), etiquetas)
    ax.set_ylim(0, max(r["p95"] for r in res) * 1.15)


def sandbox(o):
    meta, frio = cargar("vm", "sandbox_frio")
    _, pool = cargar("vm", "sandbox_pool")
    if not frio or not pool:
        return
    frio, pool = validas(frio), validas(pool)
    r = {"frio": c.resumen([f["total_ms"] for f in frio]), "pool": c.resumen([f["total_ms"] for f in pool]),
         "get": c.resumen([f["get_ms"] for f in pool]), "rec": c.resumen([f["reciclado_ms"] for f in pool])}
    nombres = {"frio": o.t("Arranque en frío (`docker run` + `exec`)", "Cold start"),
               "pool": o.t("Warm Pool (pedir + `exec`)", "Warm Pool"),
               "get": o.t("  de ello, `get_container()`", "\\quad acquire only"),
               "rec": o.t("Reciclado tras usar", "Recycling")}
    red = 1 - r["pool"]["mediana"] / r["frio"]["mediana"]
    o.cumple["reduccion_pool"] = (o.pct(red), red >= 0.75)
    for k, pre in (("frio", "Cold"), ("pool", "Pool"), ("get", "PoolGet"), ("rec", "Recycle")):
        o.macro(f"{pre}MedianMs", o.n(r[k]["mediana"]))
        o.macro(f"{pre}PNinetyFiveMs", o.n(r[k]["p95"]))
    o.macro("SandboxN", str(r["frio"]["n"]))
    o.macro("PoolReductionPct", o.pct(red))
    o.texto("## Sandbox: arranque (2.1.1 a 2.1.3)\n")
    o.tabla_md(["Medida", "n", "Mediana (ms)", "p95 (ms)", "Desv. (ms)"],
               [(nombres[k], r[k]["n"], o.n(r[k]["mediana"]), o.n(r[k]["p95"]), o.n(r[k]["desv"])) for k in r])
    o.texto(f"\nReducción de la mediana con el Warm Pool: **{red:.0%}**.\n")

    _, raf = cargar("vm", "sandbox_rafagas")
    tam, res = [], []
    if raf:
        tam = sorted({int(f["rafaga"]) for f in raf})
        res = [c.resumen([f["espera_ms"] for f in raf if int(f["rafaga"]) == t]) for t in tam]
        for t, x in zip(tam, res):
            o.macro(f"Burst{['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'][t]}PNinetyFiveMs", o.n(x["p95"]))
            o.macro(f"Burst{['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'][t]}MedianMs", o.n(x["mediana"]))
    filas_tex = [(nombres[k], r[k]["n"], o.n(r[k]["mediana"]), o.n(r[k]["p95"]), o.n(r[k]["desv"])) for k in r]
    filas_tex += [(("\\midrule " if i == 0 else "") + f"Burst of {t}: wait", x["n"], o.n(x["mediana"]), o.n(x["p95"]), o.n(x["desv"]))
                  for i, (t, x) in enumerate(zip(tam, res))]
    o.latex("sandbox", ["Measurement", "$n$", "Median (ms)", "p95 (ms)", "SD (ms)"], filas_tex,
            "Sandbox start-up latency on the production VM. The Warm Pool removes container creation from the request path; "
            "recycling happens after the response but bounds throughput when bursts exceed the pool of three. "
            "Cold start: \\texttt{docker run} + \\texttt{exec}; Warm Pool: acquire + \\texttt{exec}." + o.origen_tex(meta, "vm", "sandbox_frio"))

    fig, ax = o.figura(5.5, 3.2)
    barras_mediana_p95(o, ax, [o.t("Frío", "Cold"), "Warm Pool", o.t("Reciclado", "Recycle")], [r["frio"], r["pool"], r["rec"]], AZUL)
    ax.set_ylabel("ms")
    o.titulo(ax, "Latencia del sandbox en la VM (barra: mediana; bigote: p95)")
    o.guardar(fig, "sandbox_arranque")
    if raf:
        o.texto("\n### Ráfagas contra un pool de 3 contenedores\n")
        o.tabla_md(["Peticiones a la vez", "n", "Espera mediana (ms)", "p95 (ms)", "Máx. (ms)"],
                   [(t, x["n"], o.n(x["mediana"]), o.n(x["p95"]), o.n(x["max"])) for t, x in zip(tam, res)])
        fig, ax = o.figura(5.5, 3.2)
        barras_mediana_p95(o, ax, [str(t) for t in tam], res, AZUL)
        ax.set_xlabel(o.t("peticiones simultáneas", "concurrent requests"))
        ax.set_ylabel(o.t("espera por contenedor (ms)", "wait for a container (ms)"))
        o.titulo(ax, "Espera en ráfagas, pool de 3 (barra: mediana; bigote: p95)")
        o.guardar(fig, "sandbox_rafagas")
    o.fuente(meta, "vm", "sandbox_frio")


def sobrecoste(o):
    meta, filas = cargar("vm", "sandbox_sobrecoste")
    if not filas:
        return
    filas = validas(filas)
    progs = list(dict.fromkeys(f["programa"] for f in filas))
    r = {(p, v): c.resumen([f["ms"] for f in filas if f["programa"] == p and f["via"] == v]) for p in progs for v in ("host", "sandbox")}
    cociente = {p: r[p, "sandbox"]["mediana"] / r[p, "host"]["mediana"] for p in progs}
    dif = {p: r[p, "sandbox"]["mediana"] - r[p, "host"]["mediana"] for p in progs}
    peor = max(cociente.values()) - 1
    o.cumple["sobrecoste"] = (o.pct(peor), peor <= 0.15)
    nombre_en = {"hola": "Hello world", "mediano": "Medium file", "makefile": "Makefile project", "calculo": "Compute-bound"}
    macro_en = {"hola": "Hello", "mediano": "Medium", "makefile": "Makefile", "calculo": "Compute"}
    for p in progs:
        o.macro(f"Overhead{macro_en.get(p, p.title())}Ratio", f"{cociente[p]:.2f}")
        o.macro(f"Overhead{macro_en.get(p, p.title())}Ms", o.n(dif[p], 0))
    o.macro("OverheadMinMs", o.n(min(dif.values()), 0))
    o.macro("OverheadMaxMs", o.n(max(dif.values()), 0))
    o.texto("## Sandbox: sobrecoste de aislamiento (2.2)\n")
    o.tabla_md(["Programa", "n", "Host mediana (ms)", "Sandbox mediana (ms)", "Diferencia (ms)", "Sandbox / host"],
               [(p, r[p, "host"]["n"], o.n(r[p, "host"]["mediana"]), o.n(r[p, "sandbox"]["mediana"]), o.n(dif[p]),
                 f"x{cociente[p]:.2f}".replace(".", ",")) for p in progs])
    o.latex("overhead", ["Program", "$n$", "Host", "Sandbox", "$\\Delta$", "Ratio"],
            [(nombre_en.get(p, p), r[p, "host"]["n"], o.n(r[p, "host"]["mediana"], 0), o.n(r[p, "sandbox"]["mediana"], 0),
              o.n(dif[p], 0), f"{cociente[p]:.2f}$\\times$") for p in progs],
            "Compile-and-run time of the same program on the host and through the sandbox (medians, ms)." + o.origen_tex(meta, "vm", "sandbox_sobrecoste"))
    fig, ax = o.figura(6, 3.2)
    x = range(len(progs))
    ax.bar([i - 0.2 for i in x], [r[p, "host"]["mediana"] for p in progs], width=0.38, color=AZUL, label="host")
    ax.bar([i + 0.2 for i in x], [r[p, "sandbox"]["mediana"] for p in progs], width=0.38, color=NARANJA, label="sandbox")
    ax.set_xticks(list(x), progs if o.es else [nombre_en.get(p, p).replace(" ", "\n") for p in progs])
    ax.set_ylabel(o.t("compilar + ejecutar, mediana (ms)", "compile + run, median (ms)"))
    o.titulo(ax, "Mismo programa en el host y en el sandbox (VM)")
    ax.legend(frameon=False)
    o.guardar(fig, "sandbox_sobrecoste")
    o.fuente(meta, "vm", "sandbox_sobrecoste")


def terminacion(o):
    meta, filas = cargar("vm", "sandbox_terminacion")
    if not filas:
        return
    out = []
    for caso in dict.fromkeys(f["caso"] for f in filas):
        ff = [f for f in filas if f["caso"] == caso]
        r = c.resumen([f["total_ms"] for f in ff])
        recre = sum(f["contenedor_recreado"] == "1" for f in ff)
        restos = sum(int(f["procesos_restantes"] or 0) for f in ff)
        out.append((caso, r, recre, len(ff), restos))
        if caso == "bucle":
            exceso = r["p95"] - 30000
            o.cumple["terminacion"] = (o.t(f"{o.n(exceso, 0)} ms (incluye compilar)", f"{o.n(exceso, 0)}\\,ms (incl.\\ compile)"), None)
            o.macro("LoopMedianMs", o.n(r["mediana"], 0))
            o.macro("LoopPNinetyFiveMs", o.n(r["p95"], 0))
            o.macro("LoopRecreated", f"{recre} of {len(ff)}")
            o.macro("LoopLeftover", str(restos))
        else:
            o.macro("LoopReferenceMedianMs", o.n(r["mediana"], 0))
    o.texto("## Sandbox: bucle infinito (2.3)\n")
    o.tabla_md(["Caso", "n", "Mediana (ms)", "p95 (ms)", "Máx. (ms)", "Contenedor recreado", "Procesos que quedan"],
               [(cs, r["n"], o.n(r["mediana"]), o.n(r["p95"]), o.n(r["max"]),
                 f"{k} de {n}" if cs != "referencia" else "-", rest if cs != "referencia" else "-") for cs, r, k, n, rest in out])
    o.fuente(meta, "vm", "sandbox_terminacion")


def desconexion(o):
    meta, filas = cargar("portatil", "sandbox_desconexion")
    if not filas:
        return
    n = len(filas)
    vivo = sum(f["programa_vivo_2s_despues"] == "1" for f in filas)
    muere = c.resumen([f["ms_hasta_que_muere"] for f in filas if f["ms_hasta_que_muere"]])
    recrea = c.resumen([f["ms_hasta_recrear"] for f in filas if f["ms_hasta_recrear"]])
    sig = sum(f["siguiente_ok"] == "1" for f in filas)
    corte = float(filas[0]["corte_s"])
    o.macro("DisconnectN", str(n))
    o.macro("DisconnectAlive", f"{vivo}/{n}")
    o.macro("DisconnectCutS", o.n(corte, 0))
    o.macro("DisconnectDiesMedianS", o.n(muere["mediana"] / 1000, 1))
    o.macro("DisconnectRecreateMedianS", o.n(recrea["mediana"] / 1000, 1))
    o.macro("DisconnectNextOk", f"{sig}/{n}")
    o.texto("## Sandbox: el alumno cierra la página a mitad de la ejecución (2.3.3)\n")
    o.texto(f"API en local con un pool de 1 contenedor. Se manda un bucle infinito y se corta la conexión a los {corte:.0f} s; "
            "después se mira el contenedor desde el host cada 0,25 s.\n")
    o.tabla_md(["n", "Programa vivo 2 s después del corte", "Muere tras el corte, mediana (s)", "Máx. (s)",
                "Contenedor recreado tras el corte, mediana (s)", "Siguiente petición correcta"],
               [(n, f"{vivo} de {n}", o.n(muere["mediana"] / 1000, 1), o.n(muere["max"] / 1000, 1),
                 o.n(recrea["mediana"] / 1000, 1), f"{sig} de {n}")])
    o.fuente(meta, "portatil", "sandbox_desconexion")


def seguridad_f3(o):
    """Batería antes (vm) y después (vm_f3) del arreglo de F-3."""
    meta_a, antes = cargar("vm", "seguridad_bateria")
    meta_d, despues = cargar("vm_f3", "seguridad_bateria")
    if not antes or not despues:
        return
    md, tex = [], []
    tot_a = tot_d = n_a = n_d = 0
    for a in dict.fromkeys(f["ataque"] for f in antes):
        fa = [f for f in antes if f["ataque"] == a]
        fd = [f for f in despues if f["ataque"] == a]
        ka, kd = sum(f["contenido"] == "1" for f in fa), sum(f["contenido"] == "1" for f in fd)
        tot_a, tot_d, n_a, n_d = tot_a + ka, tot_d + kd, n_a + len(fa), n_d + len(fd)
        mec = fd[0]["mecanismo"] if fd else "-"
        if a.startswith("disco") and kd:
            mec = "raíz de solo lectura y tmpfs de 64 MB en /tmp"
        md.append((a, f"{ka} de {len(fa)}", f"{kd} de {len(fd)}", mec,
                   fd[0].get("evidencia", "-") if fd else "-"))
        if ka != kd or a.startswith("disco"):
            nombre = ATAQUES_EN.get(a, (a.replace("_", "\\_"),))[0]
            tex.append((nombre, f"{ka}/{len(fa)}", f"{kd}/{len(fd)}"))
    lo, hi = c.wilson(tot_d, n_d)
    o.macro("FixContainedRuns", str(tot_d))
    o.macro("FixAttackRuns", str(n_d))
    o.macro("FixContainmentCI", f"{o.pct(lo)}--{o.pct(hi)}")
    o.texto("## Seguridad: batería con el arreglo de F-3 (2.4.5)\n")
    o.texto("Misma batería en la VM con `--read-only` y un `tmpfs` de 64 MB en `/tmp` (copia del backend con el arreglo, "
            "sin confirmar; producción sigue en `6914f9b`).\n")
    o.tabla_md(["Ataque", "Antes (6914f9b)", "Con el arreglo", "Qué lo para ahora", "Evidencia"], md)
    o.texto(f"\nTotal: **{tot_a} de {n_a}** antes y **{tot_d} de {n_d}** con el arreglo (IC 95 % de Wilson {lo:.0%} a {hi:.0%}).\n")
    o.latex("fix", ["Attack", "Before", "After fix"], tex + [("\\midrule All classes", f"{tot_a}/{n_a}", f"{tot_d}/{n_d}")],
            "Attack battery on the production VM before and after the disk fix (read-only root, 64\\,MB \\texttt{tmpfs} on "
            "\\texttt{/tmp}); only the classes whose result changed are listed." + o.origen_tex(meta_d, "vm\\_f3", "seguridad_bateria"),
            alin="lrr")
    o.fuente(meta_d, "vm_f3", "seguridad_bateria")
    meta_ta, t_antes = cargar("vm", "seguridad_terminal")
    meta_td, t_desp = cargar("vm_f3", "seguridad_terminal")
    if t_antes and t_desp:
        md, ka_t, kd_t = [], 0, 0
        for a in dict.fromkeys(f["ataque"] for f in t_antes):
            fa = [f for f in t_antes if f["ataque"] == a]
            fd = [f for f in t_desp if f["ataque"] == a]
            ka, kd = sum(f["contenido"] == "1" for f in fa), sum(f["contenido"] == "1" for f in fd)
            ka_t, kd_t = ka_t + ka, kd_t + kd
            md.append((a, f"{ka} de {len(fa)}", f"{kd} de {len(fd)}", fd[0]["evidencia"] if fd else "-",
                       f"{sum(f['contenedor_borrado'] == '1' for f in fd)} de {len(fd)}"))
        o.macro("FixTerminalContained", str(kd_t))
        o.macro("FixTerminalRuns", str(len(t_desp)))
        o.texto("\n### Terminal con el arreglo de F-3\n")
        o.tabla_md(["Ataque", "Antes", "Con el arreglo", "Evidencia", "Contenedor borrado al cerrar"], md)
        o.texto(f"\nTotal: **{ka_t} de {len(t_antes)}** antes y **{kd_t} de {len(t_desp)}** con el arreglo.\n")
        o.fuente(meta_td, "vm_f3", "seguridad_terminal")


def seguridad(o):
    meta, filas = cargar("vm", "seguridad_bateria")
    if not filas:
        return
    ataques = list(dict.fromkeys(f["ataque"] for f in filas))
    md, tex, cont = [], [], []
    for a in ataques:
        ff = [f for f in filas if f["ataque"] == a]
        k = sum(f["contenido"] == "1" for f in ff)
        cont.append((a, k, len(ff)))
        mx = lambda col: max(float(f[col] or 0) for f in ff)  # noqa: E731
        md.append((a, f"{k} de {len(ff)}", ff[0]["mecanismo"], f"{mx('cpu_host_max'):.0f} %", f"{mx('mem_host_caida_mb'):.0f}", f"{mx('cont_pids_max'):.0f}"))
        nombre, mec = ATAQUES_EN.get(a, (a.replace("_", "\\_"), ff[0]["mecanismo"]))
        tex.append((nombre, f"{k}/{len(ff)}" if k == len(ff) else f"\\textbf{{{k}/{len(ff)}}}", mec,
                    f"{mx('cpu_host_max'):.0f}", f"{mx('mem_host_caida_mb'):.0f}"))
    tot, n = sum(k for _, k, _ in cont), sum(m for *_, m in cont)
    lo, hi = c.wilson(tot, n)
    o.cumple["contencion"] = (f"{tot}/{n}", tot == n)
    o.macro("ContainedRuns", str(tot))
    o.macro("AttackRuns", str(n))
    o.macro("ContainmentPct", o.pct(tot / n))
    o.macro("ContainmentCI", f"{o.pct(lo)}--{o.pct(hi)}")
    o.macro("AttackHostCpuMaxPct", o.pct(max(float(f["cpu_host_max"] or 0) for f in filas) / 100))
    o.macro("AttackHostMemDropMaxMb", o.n(max(float(f["mem_host_caida_mb"] or 0) for f in filas), 0))
    o.texto("## Seguridad: batería de ataques contra el Warm Pool (2.4.2, 2.4.3)\n")
    o.tabla_md(["Ataque", "Contenido", "Qué lo para", "CPU host máx.", "Caída RAM host máx. (MB)", "PIDs máx. en el contenedor"], md)
    o.texto(f"\nTasa de contención: **{tot} de {n} ({tot / n:.0%})**, intervalo de Wilson al 95 %: {lo:.0%} a {hi:.0%}.\n")
    o.latex("security", ["Attack", "Contained", "Control that stops it", "Host CPU max (\\%)", "Host RAM drop (MB)"], tex,
            f"Attack battery against the Warm Pool on the production VM, 10 runs per attack. Overall containment "
            f"{tot}/{n} (95\\% Wilson CI {o.pct(lo)}--{o.pct(hi)})." + o.origen_tex(meta, "vm", "seguridad_bateria"),
            ancha=True, alin="lrlrr")
    fig, ax = o.figura(6.5, 3.4)
    y = range(len(cont))
    ax.barh(list(y), [k for _, k, _ in cont], color=AZUL, height=0.6, label=o.t("contenido", "contained"))
    ax.barh(list(y), [m - k for _, k, m in cont], left=[k for _, k, _ in cont], color=NARANJA, height=0.6, label=o.t("no contenido", "not contained"))
    ax.set_yticks(list(y), [a for a, *_ in cont] if o.es else
                  [ATAQUES_EN.get(a, (a,))[0].replace("\\texttt{", "").replace("}", "") for a, *_ in cont])
    ax.invert_yaxis()
    ax.set_xlabel(o.t("repeticiones", "runs"))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    o.titulo(ax, f"Ataques contenidos en la VM: {tot} de {n}")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    o.guardar(fig, "seguridad_contencion")
    o.fuente(meta, "vm", "seguridad_bateria")


def rag(o):
    meta, filas = cargar("portatil", "rag_metricas")
    if not filas:
        return
    sel = [f for f in filas if f["criterio"] in ("estricto", "mas_menos_1") and f["umbral"] == "0.4"]
    tot = {f["criterio"]: f for f in sel if f["valor"] == "todas"}
    e, m1 = tot["estricto"], tot["mas_menos_1"]
    o.cumple["recall3"] = (o.n(float(e["recall@3"]), 3), float(e["recall@3"]) >= 0.88)
    for k, nombre in (("recall@1", "RecallOne"), ("recall@3", "RecallThree"), ("recall@5", "RecallFive"), ("mrr", "MRR")):
        o.macro(f"Rag{nombre}", f"{float(e[k]):.2f}")
        o.macro(f"Rag{nombre}Adjacent", f"{float(m1[k]):.2f}")
    o.macro("RagN", e["n"])
    o.macro("RagCrossTopOnePct", o.pct(float(e["top1_otra_asignatura"]), 1))
    o.macro("RagCrossTopFivePct", o.pct(float(e["alguna_otra_asignatura"]), 1))
    mp = next((f for f in sel if f["valor"] == "MP" and f["criterio"] == "estricto"), None)
    if mp and mp["alguna_otra_asignatura"]:
        o.macro("RagCrossTopFiveMPPct", o.pct(float(mp["alguna_otra_asignatura"]), 1))
    o.texto("## RAG: calidad de recuperación (2.6)\n")
    o.texto("Umbral de producción 0,40. *Estricto*: la diapositiva etiquetada; *±1*: también la anterior o la siguiente.\n")
    o.tabla_md(["Grupo", "Criterio", "n", "Recall@1", "Recall@3", "Recall@5", "MRR", "Top-1 de otra asignatura", "Alguna de otra asignatura en top-5"],
               [(f["valor"], f["criterio"].replace("mas_menos_1", "±1"), f["n"], f["recall@1"], f["recall@3"], f["recall@5"], f["mrr"],
                 f["top1_otra_asignatura"] or "-", f["alguna_otra_asignatura"] or "-") for f in sel])
    umb = [f for f in filas if f["valor"] == "todas" and f["criterio"] == "estricto"]
    o.texto("\nEfecto del umbral (total, estricto):\n")
    o.tabla_md(["Umbral", "Recall@1", "Recall@5", "Sin resultado"], [(f["umbral"], f["recall@1"], f["recall@5"], f["sin_resultado"]) for f in umb])
    grupos = [f for f in sel if f["criterio"] == "estricto"]
    o.latex("rag", ["Group", "$n$", "R@1", "R@3", "R@5", "MRR"],
            [(GRUPOS_EN.get(f["valor"], f["valor"]), f["n"], f"{float(f['recall@1']):.2f}", f"{float(f['recall@3']):.2f}",
              f"{float(f['recall@5']):.2f}", f"{float(f['mrr']):.2f}") for f in grupos],
            "Retrieval quality on 96 author-written questions (strict criterion: the labelled slide; production threshold 0.40). "
            "FP, MP and FS are the three courses." + o.origen_tex(meta, "portatil", "rag_metricas"))
    fig, ax = o.figura(6, 3.2)
    x = range(len(grupos))
    for j, (k, col) in enumerate((("recall@1", AZUL), ("recall@3", NARANJA), ("recall@5", AQUA))):
        ax.bar([i + (j - 1) * 0.26 for i in x], [float(f[k]) for f in grupos], width=0.25, color=col, label=k.replace("recall", "Recall"))
    corto_en = {"teoria": "Theory", "codigo": "Code", "erratas": "Typos", "ambigua": "Ambig."}
    ax.set_xticks(list(x), [f["valor"] if o.es else corto_en.get(f["valor"], GRUPOS_EN.get(f["valor"], f["valor"])) for f in grupos])
    if not o.es:
        ax.tick_params(axis="x", labelsize=6.5)
    ax.axvline(3.5, color=TINTA2, linewidth=0.8, linestyle=":")
    ax.set_ylim(0, 1.05)
    o.titulo(ax, "Recall@K por asignatura y por tipo de pregunta (estricto, umbral 0,40)")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12 if o.es else -0.2))
    o.guardar(fig, "rag_recall")
    o.fuente(meta, "portatil", "rag_metricas")


def corpus(o):
    meta, filas = cargar("portatil", "rag_corpus")
    if not filas:
        return
    for f in filas:
        nombre = "Total" if f["asignatura"] == "total" else f["asignatura"]
        o.macro(f"Corpus{nombre}Pdfs", f["pdfs"])
        o.macro(f"Corpus{nombre}Slides", o.n(int(f["diapositivas"]), 0))
    o.texto("## RAG: tamaño del corpus (4.3.5)\n")
    o.tabla_md(["Asignatura", "PDFs", "Diapositivas indexadas", "Caracteres medios por diapositiva"],
               [(f["asignatura"], f["pdfs"], f["diapositivas"], f["caracteres_medios"]) for f in filas])
    o.fuente(meta, "portatil", "rag_corpus")


def ruteo(o):
    meta, filas = cargar("portatil", "tutor_ruteo")
    if not filas:
        return
    cls = ["ninguna", "apuntes", "compilar", "internet"]
    m = collections.Counter((f["esperada"], f["primera"]) for f in filas)
    ok = sum(f["acierto_primera"] == "1" for f in filas)
    inc = sum(f["acierto_incluida"] == "1" for f in filas)
    lo, hi = c.wilson(ok, len(filas))
    o.cumple["ruteo"] = (f"{ok}/{len(filas)}", ok / len(filas) >= 0.96)
    o.macro("RoutingCorrect", str(ok))
    o.macro("RoutingN", str(len(filas)))
    o.macro("RoutingIncluded", str(inc))
    o.macro("RoutingPct", o.pct(ok / len(filas)))
    o.macro("RoutingCI", f"{o.pct(lo)}--{o.pct(hi)}")
    o.texto("## Tutor: ruteo de herramientas (2.7.1 a 2.7.3)\n")
    o.texto(f"Acierto con la primera herramienta: **{ok} de {len(filas)}**; con la esperada en alguna llamada: {inc} de {len(filas)}.\n")
    o.texto("Matriz de confusión (filas: esperada; columnas: primera herramienta usada):\n")
    o.tabla_md(["Esperada \\ usada"] + cls, [[e] + [m[e, u] for u in cls] for e in cls])
    o.latex("routing", ["Expected $\\downarrow$ / used $\\rightarrow$"] + [HERRAMIENTAS_EN[u] for u in cls],
            [[HERRAMIENTAS_EN[e]] + [f"\\textbf{{{m[e, u]}}}" if e == u else m[e, u] for u in cls] for e in cls],
            f"Tool-routing confusion matrix over 50 labelled scenarios (first tool invoked). Accuracy {ok}/{len(filas)} "
            f"(95\\% Wilson CI {o.pct(lo)}--{o.pct(hi)})." + o.origen_tex(meta, "portatil", "tutor_ruteo"))
    datos = [[m[e, u] for u in cls] for e in cls]
    fig, ax = o.figura(4.4, 3.6)
    ax.imshow(datos, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("azul", ["#f1f6fd", "#184f95"]))
    for i in range(4):
        for j in range(4):
            v = datos[i][j]
            ax.text(j, i, v, ha="center", va="center", color="white" if v > 8 else TINTA, fontsize=10 if o.es else 8)
    etiquetas = cls if o.es else [HERRAMIENTAS_EN[u] for u in cls]
    ax.set_xticks(range(4), etiquetas)
    ax.set_yticks(range(4), etiquetas)
    ax.set_xlabel(o.t("primera herramienta usada", "first tool invoked"))
    ax.set_ylabel(o.t("esperada", "expected"))
    ax.grid(False)
    o.titulo(ax, f"Ruteo del tutor: {ok} de {len(filas)} aciertos")
    o.guardar(fig, "tutor_ruteo")
    o.fuente(meta, "portatil", "tutor_ruteo")


def escaneos(o):
    meta, filas = cargar("portatil", "escaneos_resumen")
    if not filas:
        return
    o.texto("## Escaneos de imagen, dependencias y secretos (2.4.9)\n")
    o.tabla_md(["Herramienta", "Objetivo", "Gravedad", "Hallazgos", "Con arreglo publicado", "Dónde"],
               [(f["herramienta"], f["objetivo"], f["gravedad"], f["hallazgos"], f["con_arreglo"] or "-", f["detalle"] or "-") for f in filas])
    get = lambda h, g: next((f for f in filas if f["herramienta"] == h and f["gravedad"] == g), None)  # noqa: E731
    for h, g, nombre in (("trivy", "CRITICAL", "TrivyCritical"), ("trivy", "HIGH", "TrivyHigh"), ("gitleaks", "secreto", "GitleaksSecrets")):
        f = get(h, g)
        if f:
            o.macro(nombre, f["hallazgos"])
    pip = [f for f in filas if f["herramienta"] == "pip-audit"]
    if pip:
        o.macro("PipAuditAdvisories", str(sum(int(f["hallazgos"]) for f in pip)))
    o.fuente(meta, "portatil", "escaneos_resumen")


def terminal(o):
    meta, filas = cargar("vm", "seguridad_terminal")
    if not filas:
        return
    nombres_en = {"red": "Network", "bomba_fork": "Fork bomb", "memoria": "Memory", "disco": "Disk (1\\,GB)", "cpu": "CPU spin"}
    md, tex = [], []
    tot = n = 0
    for a in dict.fromkeys(f["ataque"] for f in filas):
        ff = [f for f in filas if f["ataque"] == a]
        k = sum(f["contenido"] == "1" for f in ff)
        borr = sum(f["contenedor_borrado"] == "1" for f in ff)
        tot, n = tot + k, n + len(ff)
        mx = lambda col: max(float(f[col] or 0) for f in ff)  # noqa: E731
        md.append((a, f"{k} de {len(ff)}", ff[0]["mecanismo"], ff[0]["evidencia"], f"{mx('cpu_max'):.0f} %", f"{mx('mem_max_mb'):.0f}",
                   f"{mx('pids_max'):.0f}", f"{borr} de {len(ff)}"))
        mec = ff[0]["mecanismo"].replace("ninguno previsto", "none configured")
        mec = f"\\texttt{{{mec}}}" if mec.startswith("--") else mec
        tex.append((nombres_en.get(a, a), f"{k}/{len(ff)}" if k == len(ff) else f"\\textbf{{{k}/{len(ff)}}}", mec,
                    f"{mx('cpu_max'):.0f}", f"{mx('mem_max_mb'):.0f}"))
    o.macro("TerminalContained", str(tot))
    o.macro("TerminalRuns", str(n))
    o.texto("## Seguridad: ataques desde la terminal interactiva (2.4.4)\n")
    o.texto("Contenedor de la terminal por WebSocket (`--memory 512m`, `--cpus 1`, `--pids-limit 100`), 10 repeticiones por ataque. "
            "CPU, memoria y PIDs son los del contenedor.\n")
    o.tabla_md(["Ataque", "Contenido", "Qué lo para", "Evidencia", "CPU máx.", "Memoria máx. (MB)", "PIDs máx.", "Contenedor borrado al cerrar"], md)
    o.latex("terminal", ["Attack", "Contained", "Control", "CPU", "Mem"], tex,
            f"Attacks from the interactive terminal container on the production VM, 10 runs each ({tot}/{n} contained). "
            "CPU (\\%) and Mem (MB) are the container's own peaks; the container was removed on disconnect in every run."
            + o.origen_tex(meta, "vm", "seguridad_terminal"), alin="lrlrr")
    o.fuente(meta, "vm", "seguridad_terminal")


def terminal_huerfana(o):
    meta, filas = cargar("portatil", "seguridad_terminal_huerfana")
    if not filas:
        return
    n = len(filas)
    vivas = sum(f["sigue_viva"] == "1" for f in filas)
    o.macro("OrphanAlive", f"{vivas}/{n}")
    o.macro("OrphanWaitS", o.n(float(filas[0]["espera_s"]), 0))
    limpias = sum(f.get("viva_tras_reiniciar") == "0" for f in filas)
    if "viva_tras_reiniciar" in filas[0]:
        o.macro("OrphanCleanedOnRestart", f"{limpias}/{n}")
    o.texto("## Seguridad: terminales huérfanas si la API muere (F-7)\n")
    o.texto("API en local con una terminal abierta por WebSocket; se mata solo el proceso de la API con SIGKILL y se mira "
            f"si el contenedor de la terminal sigue vivo {filas[0]['espera_s']} s después.\n")
    o.texto("Después se arranca la API otra vez (como un reinicio de pm2), con el arreglo de F-7.\n")
    o.tabla_md(["n", "Terminal abierta", "Contenedor vivo tras matar la API", "Borrado al reiniciar la API"],
               [(n, f"{sum(f['terminal_abierta'] == '1' for f in filas)} de {n}", f"{vivas} de {n}",
                 f"{limpias} de {n}" if "viva_tras_reiniciar" in filas[0] else "-")])
    o.fuente(meta, "portatil", "seguridad_terminal_huerfana")


def docker_bench(o):
    ruta = os.path.join(RES, "escaneos", "vm", "docker_bench_salida.log.json")
    if not os.path.exists(ruta):
        return
    import json
    with open(ruta, encoding="utf-8") as f:
        d = json.load(f)
    cnt = collections.Counter()
    por_sec = collections.defaultdict(collections.Counter)
    sandbox_warn = []
    for s in d["tests"]:
        for r in s["results"]:
            cnt[r["result"]] += 1
            por_sec[s["desc"]][r["result"]] += 1
            items = r.get("items") or []
            if r["result"] == "WARN" and any(str(i).startswith(("tutor_warm", "tutor_mcp")) for i in items):
                sandbox_warn.append(f"{r['id']} {r['desc'].split(' (')[0]}")
    for k, nombre in (("PASS", "Pass"), ("WARN", "Warn"), ("INFO", "Info"), ("NOTE", "Note")):
        o.macro(f"DockerBench{nombre}", str(cnt[k]))
    o.macro("DockerBenchChecks", str(d.get("checks", sum(cnt.values()))))
    o.macro("DockerBenchSandboxWarn", str(len(sandbox_warn)))
    o.texto("## Seguridad: docker-bench-security en la VM (2.4.10)\n")
    o.tabla_md(["Sección", "PASS", "WARN", "INFO", "NOTE"],
               [(sec, v["PASS"], v["WARN"], v["INFO"], v["NOTE"]) for sec, v in por_sec.items()] +
               [("**Total**", cnt["PASS"], cnt["WARN"], cnt["INFO"], cnt["NOTE"])])
    o.texto("\nAvisos que afectan a los contenedores de TutorIA (`tutor_warm_*`, `tutor_mcp_*`):\n\n" +
            "\n".join(f"- {w}" for w in sandbox_warn) +
            "\n\nLos avisos 5.3, 5.11, 5.26 y 5.29 (sin SELinux, memoria, `no-new-privileges` ni límite de PIDs) solo los dan "
            "cinco contenedores con nombre aleatorio que no son del pool; no se identificó qué los lanzó.\n")
    o.texto(f"\n*Fuente: `resultados/escaneos/vm/docker_bench_salida.log.json` y `META.txt`, docker-bench-security v1.6.1.*\n")


def ttft(o):
    meta, filas = cargar("vm", "tutor_ttft")
    if not filas:
        return
    rutas = list(dict.fromkeys(f["ruta"] for f in filas))
    en = {"rapida": "Fast path (no tool)", "rag": "Notes search (RAG)", "compilacion": "Compile tool"}
    corto_en = {"rapida": "Fast", "rag": "RAG", "compilacion": "Compile"}
    macro_en = {"rapida": "Fast", "rag": "Rag", "compilacion": "Compile"}
    r, tot, ok = {}, {}, {}
    for ru in rutas:
        ff = [f for f in filas if f["ruta"] == ru]
        bien = [f for f in ff if f["estado"] == "200"]
        ok[ru] = (len(bien), len(ff))
        r[ru] = c.resumen([f["ttft_ms"] for f in bien])
        tot[ru] = c.resumen([f["total_ms"] for f in bien])
        o.macro(f"Ttft{macro_en[ru]}MedianMs", o.n(r[ru]["mediana"], 0))
        o.macro(f"Ttft{macro_en[ru]}PNinetyFiveMs", o.n(r[ru]["p95"], 0))
    o.macro("TtftN", str(r[rutas[0]]["n"]))
    o.macro("TtftRequests", str(len(filas)))
    if "rapida" in r:
        p = r["rapida"]["p95"]
        o.cumple["ttft_rapida"] = (o.t(f"{o.n(p, 0)} ms", f"{o.n(p, 0)}\\,ms"), p <= 1000)
    agente = [ru for ru in ("rag", "compilacion") if ru in r]
    if agente:
        peor = max(agente, key=lambda ru: r[ru]["p95"])
        p = r[peor]["p95"]
        o.cumple["ttft_agente"] = (o.t(f"{o.n(p, 0)} ms ({peor})", f"{o.n(p, 0)}\\,ms ({corto_en[peor]})"), p <= 10000)
    o.texto("## Tutor: tiempo hasta el primer token por ruta (2.7.4)\n")
    o.texto("API real de producción por túnel SSH, una petición cada 6 s, LLM real.\n")
    o.tabla_md(["Ruta", "Respuestas 200", "TTFT mediana (ms)", "TTFT p95 (ms)", "TTFT máx. (ms)", "Total mediana (ms)"],
               [(ru, f"{ok[ru][0]} de {ok[ru][1]}", o.n(r[ru]["mediana"], 0), o.n(r[ru]["p95"], 0), o.n(r[ru]["max"], 0),
                 o.n(tot[ru]["mediana"], 0)) for ru in rutas])
    o.latex("ttft", ["Path", "$n$", "Median", "p95", "Max"],
            [(en.get(ru, ru), r[ru]["n"], o.n(r[ru]["mediana"], 0), o.n(r[ru]["p95"], 0), o.n(r[ru]["max"], 0)) for ru in rutas],
            "Time to first token (ms) through the production API with the real LLM, one request every 6\\,s. "
            "On the tool paths the first token arrives after the tool returns." + o.origen_tex(meta, "vm", "tutor_ttft"))
    fig, ax = o.figura(5.5, 3.2)
    barras_mediana_p95(o, ax, rutas if o.es else [corto_en[ru] for ru in rutas], [r[ru] for ru in rutas], AZUL)
    ax.axhline(1000, color=NARANJA, linewidth=1, linestyle="--")
    ax.axhline(10000, color=NARANJA, linewidth=1, linestyle=":")
    ax.set_ylabel(o.t("TTFT (ms)", "TTFT (ms)"))
    o.titulo(ax, "TTFT por ruta (barra: mediana; bigote: p95; líneas: objetivos 1 s y 10 s)")
    o.guardar(fig, "tutor_ttft")
    o.fuente(meta, "vm", "tutor_ttft")


def rag_caches(o):
    meta, filas = cargar("vm", "rag_caches")
    if not filas:
        return
    casos = list(dict.fromkeys(f["caso"] for f in filas))
    r = {k: c.resumen([f["ms"] for f in filas if f["caso"] == k]) for k in casos}
    es = {"sin_cache": "Sin caché (embedding + búsqueda)", "cache_embedding": "Caché de embedding (solo búsqueda)",
          "cache_resultado": "Caché de resultado"}
    en = {"sin_cache": "No cache", "cache_embedding": "Embedding cached", "cache_resultado": "Result cached"}
    macro_en = {"sin_cache": "NoCache", "cache_embedding": "EmbCache", "cache_resultado": "ResultCache"}
    for k in casos:
        o.macro(f"Rag{macro_en[k]}MedianMs", o.n(r[k]["mediana"], 3 if r[k]["mediana"] < 1 else 0))
        o.macro(f"Rag{macro_en[k]}PNinetyFiveMs", o.n(r[k]["p95"], 3 if r[k]["p95"] < 1 else 0))
    o.texto("## RAG: efecto de las cachés (2.6.8)\n")
    o.tabla_md(["Caso", "n", "Mediana (ms)", "p95 (ms)", "Máx. (ms)"],
               [(es.get(k, k), r[k]["n"], o.n(r[k]["mediana"], 3 if r[k]["mediana"] < 1 else 1),
                 o.n(r[k]["p95"], 3 if r[k]["p95"] < 1 else 1), o.n(r[k]["max"], 3 if r[k]["max"] < 1 else 1)) for k in casos])
    o.latex("ragcache", ["Case", "$n$", "Median (ms)", "p95 (ms)"],
            [(en.get(k, k), r[k]["n"], o.n(r[k]["mediana"], 3 if r[k]["mediana"] < 1 else 0),
              o.n(r[k]["p95"], 3 if r[k]["p95"] < 1 else 0)) for k in casos],
            "Retrieval latency on the production VM by cache state." + o.origen_tex(meta, "vm", "rag_caches"))
    o.fuente(meta, "vm", "rag_caches")


def fallback(o):
    meta, filas = cargar("portatil", "tutor_fallback")
    if not filas:
        return
    casos = list(dict.fromkeys(f["caso"] for f in filas))
    o.macro("FallbackTurns", str(len(filas)))
    es = {"normal": "Gemini disponible", "gemini_caida": "Gemini caído (clave inválida)"}
    en = {"normal": "Gemini available", "gemini_caida": "Gemini down (invalid key)"}
    macro_en = {"normal": "Normal", "gemini_caida": "GeminiDown"}
    md, tex = [], []
    for k in casos:
        ff = [f for f in filas if f["caso"] == k]
        r = c.resumen([f["ms"] for f in ff])
        resp = sum(f["respondio"] == "1" for f in ff)
        groq = sum(f["paso_a_groq"] == "1" for f in ff)
        o.macro(f"Fallback{macro_en[k]}Answered", f"{resp}/{len(ff)}")
        o.macro(f"Fallback{macro_en[k]}Groq", f"{groq}/{len(ff)}")
        o.macro(f"Fallback{macro_en[k]}MedianMs", o.n(r["mediana"], 0))
        o.macro(f"Fallback{macro_en[k]}PNinetyFiveMs", o.n(r["p95"], 0))
        md.append((es.get(k, k), len(ff), f"{resp} de {len(ff)}", f"{groq} de {len(ff)}", o.n(r["mediana"], 0), o.n(r["p95"], 0)))
        tex.append((en.get(k, k), len(ff), f"{resp}/{len(ff)}", f"{groq}/{len(ff)}", o.n(r["mediana"], 0), o.n(r["p95"], 0)))
    o.texto("## Tutor: paso de Gemini a Groq (2.7.5)\n")
    o.texto(f"Gemini `{meta.get('gemini', '?')}`, Groq `{meta.get('groq', '?')}`, modo {meta.get('modo', '?')}.\n")
    o.tabla_md(["Caso", "n", "Respondió", "Pasó a Groq", "Mediana (ms)", "p95 (ms)"], md)
    o.texto("\nCon Gemini caído, la búsqueda en apuntes también falla: los embeddings usan la misma clave (F-4).\n")
    o.latex("fallback", ["Case", "$n$", "Answered", "Groq", "Median", "p95"], tex,
            "Provider fallback: end-to-end latency (ms) of a tutor turn with Gemini available and with an invalid Gemini key."
            + o.origen_tex(meta, "portatil", "tutor_fallback"), alin="lrrrrr")
    o.fuente(meta, "portatil", "tutor_fallback")


def fuga(o):
    metas, conds = {}, {}
    for cond in ("con_guardrail", "sin_guardrail"):
        m, f = cargar("portatil", f"tutor_fuga_{cond}")
        if f:
            metas[cond], conds[cond] = m, f
    meta_j, juez = cargar("portatil", "tutor_fuga_juez")
    if len(conds) < 2 or not juez:
        return
    o.macro("LeakTurns", str(sum(len(f) for f in conds.values())))
    o.macro("JudgeCalls", str(len(juez)))
    es = {"con_guardrail": "Con grafo", "sin_guardrail": "Sin grafo"}
    en = {"con_guardrail": "Full graph", "sin_guardrail": "No graph"}
    macro_en = {"con_guardrail": "Graph", "sin_guardrail": "NoGraph"}
    md, tex, lat_md = [], [], []
    for cond, filas in conds.items():
        jc = [j for j in juez if j["condicion"] == cond]
        ataque = [j for j in jc if j["categoria"] != "legitima"]
        leg = [j for j in jc if j["categoria"] == "legitima"]
        k = sum(j["etiqueta"] == "fuga" for j in ataque)
        lo, hi = c.wilson(k, len(ataque))
        b = sum(j["sin_ayuda"] == "1" for j in leg)
        blo, bhi = c.wilson(b, len(leg))
        ids_leg = sorted({j["id"] for j in leg})
        ids_bloq = sorted({j["id"] for j in leg if j["sin_ayuda"] == "1"})
        r = c.resumen([f["ms"] for f in filas])
        iny = sum(int(f["inyeccion_detectada"]) for f in filas)
        acc = sum(int(f["sospecha"]) + int(f["reescrita"]) + int(f["mensaje_fijo"]) for f in filas)
        mc = macro_en[cond]
        o.macro(f"Leak{mc}", f"{k}/{len(ataque)}")
        o.macro(f"Leak{mc}CI", f"{o.pct(lo, 1)}--{o.pct(hi, 1)}")
        o.macro(f"Blocked{mc}", f"{b}/{len(leg)}")
        o.macro(f"Blocked{mc}CI", f"{o.pct(blo, 1)}--{o.pct(bhi, 1)}")
        o.macro(f"Leak{mc}MedianMs", o.n(r["mediana"], 0))
        o.macro(f"Leak{mc}PNinetyFiveMs", o.n(r["p95"], 0))
        o.macro(f"Leak{mc}Injection", str(iny))
        o.macro(f"Leak{mc}GuardActions", str(acc))
        if cond == "con_guardrail":
            o.macro("LeakAttackN", str(len(ataque)))
            o.macro("LeakPromptsLegit", str(len(ids_leg)))
            o.macro("LeakLegitNeverBlocked", str(len(ids_leg) - len(ids_bloq)))
            o.cumple["fuga"] = (o.t(f"{k}/{len(ataque)} (juez automático)", f"{k}/{len(ataque)} (LLM judge)"), k == 0)
            o.cumple["legitimos"] = (o.t(f"{len(ids_leg) - len(ids_bloq)}/{len(ids_leg)}", f"{len(ids_leg) - len(ids_bloq)}/{len(ids_leg)}"),
                                     not ids_bloq)
        md.append((es[cond], f"{k} de {len(ataque)}", f"{o.pct(lo, 1)} a {o.pct(hi, 1)}", f"{b} de {len(leg)}",
                   ", ".join(ids_bloq) or "-", iny, acc))
        tex.append((en[cond], f"{k}/{len(ataque)}", f"{o.pct(lo, 1)}--{o.pct(hi, 1)}", f"{b}/{len(leg)}", iny, acc))
        lat_md.append((es[cond], r["n"], o.n(r["mediana"], 0), o.n(r["p95"], 0), o.n(r["media"], 0)))
    meta = metas["con_guardrail"]
    o.texto("## Tutor: fuga de soluciones con y sin grafo (2.8.3 y 2.8.4)\n")
    o.texto("50 prompts (25 directos, 15 de presión, 10 legítimos) x 3 repeticiones por condición. *Sin grafo* (`TUTOR_GRAPH=0`) "
            "apaga el grafo entero: guardia de entrada, formato y cita, guardrail de salida y tope de herramientas. "
            "Etiquetas del juez automático (Groq, temperatura 0); falta la puntuación a mano del autor.\n")
    o.tabla_md(["Condición", "Fugas en ataques", "IC 95 % (Wilson)", "Legítimas sin ayuda", "Prompts legítimos bloqueados",
                "Inyección detectada", "Actuaciones del guardrail de salida"], md)
    o.texto("\nLatencia por turno:\n")
    o.tabla_md(["Condición", "n", "Mediana (ms)", "p95 (ms)", "Media (ms)"], lat_md)
    o.latex("leak", ["Condition", "Leaks", "95\\% CI", "Unhelpful", "Inj.", "Guard"], tex,
            "Solution leakage over 40 attack prompts $\\times$3 and 10 legitimate prompts $\\times$3, labelled by an LLM judge "
            "(manual scoring pending). \\emph{Unhelpful}: legitimate requests left without help. \\emph{Inj.}: input-guard "
            "injection detections; \\emph{Guard}: output-guard interventions. \\emph{No graph} disables the whole graph, "
            "not only the output guard." + o.origen_tex(meta_j, "portatil", "tutor_fuga_juez"), alin="lrlrrr")
    o.fuente(meta, "portatil", "tutor_fuga_con_guardrail")


def _ventana_monitor(monitor, t0, t1):
    """Resumen del monitor de la VM entre dos instantes (epoch); None si no hay muestras."""
    m = [f for f in monitor if t0 <= float(f["epoch_s"]) <= t1]
    if not m:
        return None
    return {"cpu_med": c.resumen([f["cpu_pct"] for f in m])["mediana"], "cpu_max": max(float(f["cpu_pct"]) for f in m),
            "mem_min": min(float(f["mem_disp_mb"]) for f in m), "cont_max": max(int(f["contenedores_bench"]) for f in m),
            "rss_max": max(float(f["rss_api_mb"] or 0) for f in m)}


def carga(o):
    meta, ex = cargar("vm", "carga_execute")
    if not ex:
        return
    monitor = []
    carpeta = os.path.join(RES, "vm")
    for nombre in sorted(os.listdir(carpeta)):
        if nombre.startswith("monitor_carga") and nombre.endswith(".csv"):
            meta_mon, filas_mon = c.leer_csv(os.path.join(carpeta, nombre))
            monitor += filas_mon
    grupos = list(dict.fromkeys((f["modo"], int(f["vus"])) for f in ex))
    filas_md, filas_tex, fig_datos = [], [], []
    docs_p95_max, exec_p95_10, cinco = 0.0, None, 0
    for modo, vus in grupos:
        ff = [f for f in ex if f["modo"] == modo and int(f["vus"]) == vus]
        exe = [f for f in ff if f["metrica"] == "exec_ms"]
        docs = [f for f in ff if f["metrica"] == "docs_ms"]
        reps = len({f["rep"] for f in ff})
        dur_min = reps * ({"constante": 180, "rampa": 300, "pico": 62}[modo]) / 60
        res = collections.Counter(f["resultado"] for f in exe)
        cinco += res["error_5xx"]
        r_all = c.resumen([f["ms"] for f in exe])
        r_ok = c.resumen([f["ms"] for f in exe if f["resultado"] == "ok"])
        r_docs = c.resumen([f["ms"] for f in docs])
        epochs = [float(f["epoch_s"]) for f in ff]
        mon = _ventana_monitor(monitor, min(epochs), max(epochs)) if monitor else None
        if modo == "constante":
            docs_p95_max = max(docs_p95_max, r_docs["p95"])
            if vus == 10:
                exec_p95_10 = r_all["p95"]
            fig_datos.append((vus, res["ok"] / dur_min, res["pool_ocupado"] / dur_min, r_ok["p95"]))
            mc = {10: "Ten", 50: "Fifty", 100: "Hundred"}[vus]
            o.macro(f"Load{mc}ExecMedianS", o.n(r_all["mediana"] / 1000, 1))
            o.macro(f"Load{mc}ExecPNinetyFiveS", o.n(r_all["p95"] / 1000, 1))
            o.macro(f"Load{mc}ExecPNinetyNineS", o.n(r_all["p99"] / 1000, 1))
            o.macro(f"Load{mc}Busy", f"{res['pool_ocupado']}/{len(exe)}")
            o.macro(f"Load{mc}BusyPct", o.pct(res["pool_ocupado"] / len(exe)))
            o.macro(f"Load{mc}OkPerMin", o.n(res["ok"] / dur_min, 0))
            o.macro(f"Load{mc}DocsPNinetyFiveMs", o.n(r_docs["p95"], 0))
            if mon:
                o.macro(f"Load{mc}CpuMaxPct", o.pct(mon["cpu_max"] / 100))
                o.macro(f"Load{mc}CpuMedianPct", o.pct(mon["cpu_med"] / 100))
                o.macro(f"Load{mc}MemMinMb", o.n(mon["mem_min"], 0))
        nombre = {"constante": o.t(f"{vus} constantes", f"{vus} constant"), "rampa": o.t(f"rampa 0 a {vus}", f"ramp 0--{vus}"),
                  "pico": o.t(f"pico de {vus}", f"spike to {vus}")}[modo]
        otros = len(exe) - res["ok"] - res["pool_ocupado"]
        por_min = o.n(res["ok"] / dur_min, 0) if modo == "constante" else "-"
        filas_md.append((nombre, reps, len(exe), res["ok"], res["pool_ocupado"], otros, por_min,
                         o.n(r_all["mediana"] / 1000, 1), o.n(r_all["p95"] / 1000, 1), o.n(r_all["p99"] / 1000, 1),
                         o.n(r_docs["p95"], 0), f"{mon['cpu_med']:.0f} / {mon['cpu_max']:.0f} %" if mon else "-",
                         o.n(mon["mem_min"], 0) if mon else "-", o.n(mon["rss_max"], 0) if mon else "-",
                         mon["cont_max"] if mon else "-"))
        filas_tex.append((nombre, len(exe), res["ok"], res["pool_ocupado"], por_min if modo == "constante" else "--",
                          o.n(r_all["mediana"] / 1000, 1), o.n(r_all["p95"] / 1000, 1), o.n(r_docs["p95"], 0),
                          f"{mon['cpu_max']:.0f}" if mon else "--"))
    o.cumple["docs_p95"] = (o.t(f"{o.n(docs_p95_max, 0)} ms (peor nivel)", f"{o.n(docs_p95_max, 0)}\\,ms (worst level)"), docs_p95_max <= 1000)
    if exec_p95_10 is not None:
        o.cumple["execute_p95"] = (o.t(f"{o.n(exec_p95_10 / 1000, 1)} s", f"{o.n(exec_p95_10 / 1000, 1)}\\,s"), exec_p95_10 <= 10000)
    o.macro("LoadDocsPNinetyFiveMaxMs", o.n(docs_p95_max, 0))
    o.macro("LoadAcquireTimeoutS", "30")
    o.texto("## Carga: /api/execute con sonda a /docs (2.5.2 a 2.5.4, 2.5.6, 2.5.7)\n")
    o.texto("k6 en el portátil contra una instancia aparte de la API en la VM (puerto 8100, pool propio de 3 contenedores, "
            "LLM simulado), por túnel SSH. Cada cliente compila un programa pequeño cada 2,5 s; constante: 180 s por "
            "repetición, 3 repeticiones; rampa de 0 a 100 en 300 s y pico de 0 a 100 en 1 s (60 s), una vez cada uno. "
            "*Pool ocupado*: la API espera 30 s (`ACQUIRE_TIMEOUT_S`) y devuelve «servidor ocupado» con estado 200. "
            "CPU, memoria disponible y contenedores salen del monitor de la VM en la misma ventana.\n")
    o.tabla_md(["Nivel", "Reps", "Peticiones", "Completadas", "Pool ocupado", "Otras", "Completadas/min",
                "Mediana (s)", "p95 (s)", "p99 (s)", "/docs p95 (ms)", "CPU VM med./máx.", "RAM disp. mín. (MB)", "RSS API máx. (MB)", "Contenedores máx."],
               filas_md)
    o.latex("load", ["Level", "Req.", "Done", "Busy", "Done/min", "Median (s)", "p95 (s)", "\\texttt{/docs} p95 (ms)", "CPU max (\\%)"],
            filas_tex,
            "Load on \\texttt{/api/execute} through a separate API instance on the production VM (pool of three, mocked LLM). "
            "Each virtual client submits a small program every 2.5\\,s; latencies include requests that waited the 30\\,s "
            "acquire timeout and were answered \\emph{busy}. \\texttt{/docs} is probed in parallel. No request returned 5xx."
            + o.origen_tex(meta, "vm", "carga_execute"), ancha=True)
    if fig_datos:
        fig, ax = o.figura(5.5, 3.2)
        x = range(len(fig_datos))
        ax.bar(list(x), [d[1] for d in fig_datos], width=0.55, color=AZUL, label=o.t("completadas", "completed"))
        ax.bar(list(x), [d[2] for d in fig_datos], width=0.55, bottom=[d[1] for d in fig_datos], color=NARANJA,
               label=o.t("pool ocupado (30 s de espera)", "busy (after 30 s wait)"))
        for i, d in enumerate(fig_datos):
            ax.annotate(o.t(f"p95 {d[3] / 1000:.1f} s", f"p95 {d[3] / 1000:.1f} s"), (i, d[1] + d[2]), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9 if o.es else 7, color=TINTA)
        ax.set_xticks(list(x), [str(d[0]) for d in fig_datos])
        ax.set_xlabel(o.t("clientes concurrentes", "concurrent clients"))
        ax.set_ylabel(o.t("peticiones por minuto", "requests per minute"))
        ax.set_ylim(0, max(d[1] + d[2] for d in fig_datos) * 1.18)
        o.titulo(ax, "Compilaciones por minuto con un pool de 3 (p95 de las completadas)")
        ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.2))
        o.guardar(fig, "carga_execute")
    o.fuente(meta, "vm", "carga_execute")

    meta_c, chat = cargar("vm", "carga_chat")
    if chat:
        md, tex = [], []
        for k in sorted({int(f["clientes"]) for f in chat}):
            ff = [f for f in chat if int(f["clientes"]) == k]
            bien = [f for f in ff if f["estado"] == "200"]
            cinco += sum(f["estado"].startswith("5") for f in ff)
            r = c.resumen([f["ttft_ms"] for f in bien])
            rt = c.resumen([f["total_ms"] for f in bien])
            reps = len({f["rep"] for f in ff})
            md.append((k, reps, len(ff), len(bien), o.n(len(ff) / (reps * 3), 0), o.n(r["mediana"], 0), o.n(r["p95"], 0),
                       o.n(r["p99"], 0), o.n(rt["mediana"], 0)))
            tex.append((k, len(ff), len(bien), o.n(r["mediana"], 0), o.n(r["p95"], 0), o.n(r["p99"], 0)))
            o.macro(f"LoadChat{ {10: 'Ten', 50: 'Fifty', 100: 'Hundred'}[k] }TtftPNinetyFiveMs", o.n(r["p95"], 0))
        o.macro("LoadChatRequests", o.n(len(chat), 0))
        o.texto("\n### Chat por SSE con LLM simulado (2.5.2, 2.5.3)\n")
        o.texto(f"LLM simulado: {meta_c.get('llm', '?')}. 180 s por repetición. La CPU de la cabecera del CSV es la del "
                "portátil (el cliente); el servidor es la instancia de pruebas en la VM.\n")
        o.tabla_md(["Clientes", "Reps", "Peticiones", "Estado 200", "Peticiones/min", "TTFT mediana (ms)", "TTFT p95 (ms)",
                    "TTFT p99 (ms)", "Total mediana (ms)"], md)
        o.latex("loadchat", ["Clients", "Req.", "200", "Median", "p95", "p99"], tex,
                "Chat streaming under load with a mocked LLM (100\\,ms to first token): time to first token (ms) "
                "over three 180\\,s repetitions per level. This isolates the API and graph overhead from provider latency."
                + o.origen_tex(meta_c, "vm", "carga_chat"))
        o.fuente(meta_c, "vm", "carga_chat")
    o.cumple["errores_5xx"] = (str(cinco), cinco == 0)
    o.macro("LoadFiveXX", str(cinco))

    meta_l, lim = cargar("vm", "carga_rate_limit")
    if lim:
        md, tex = [], []
        for ep, pat in dict.fromkeys((f["endpoint"], f["patron"]) for f in lim):
            ff = [f for f in lim if f["endpoint"] == ep and f["patron"] == pat]
            acc = [int(f["aceptadas"]) for f in ff]
            esp = int(ff[0]["esperadas"])
            ok = all(abs(a - esp) <= 1 for a in acc)
            md.append((ep, pat, len(ff), ", ".join(map(str, acc)), esp, o.t("sí", "yes") if ok else "no"))
            tex.append((f"\\texttt{{{ep}}}", {"uniforme": "uniform", "rafaga": "burst"}.get(pat, pat), len(ff),
                        ", ".join(map(str, acc)), esp))
            if ep == "chat" and pat == "uniforme":
                o.cumple["limitador"] = (", ".join(map(str, acc)), ok)
        exactas = sum(int(f["aceptadas"]) == int(f["esperadas"]) for f in lim)
        o.macro("LimiterExact", f"{exactas}/{len(lim)}")
        o.texto("\n### Precisión del limitador (2.5.5)\n")
        o.texto("60 peticiones con la misma identidad: *uniforme*, repartidas en 60 s; *ráfaga*, seguidas. Límites: 15/min en el "
                "chat y 30/min en /api/execute.\n")
        o.tabla_md(["Endpoint", "Patrón", "Reps", "Aceptadas por prueba", "Esperadas", "Dentro de ±1"], md)
        o.latex("limiter", ["Endpoint", "Pattern", "Runs", "Accepted", "Expected"], tex,
                "Rate-limiter accuracy: 60 requests from one identity, spread over 60\\,s (uniform) or back to back (burst)."
                + o.origen_tex(meta_l, "vm", "carga_rate_limit"), alin="llrlr")
        o.fuente(meta_l, "vm", "carga_rate_limit")

    meta_e, ev = cargar("portatil", "seguridad_limitador")
    if ev:
        en = {"misma_ip": "Same forwarded IP", "sin_cabeceras": "No identity headers", "xff_rotada": "Rotating \\texttt{X-Forwarded-For}",
              "bearer_falso": "Random unverified \\texttt{Bearer}"}
        md, tex = [], []
        for est in dict.fromkeys(f["estrategia"] for f in ev):
            ff = [f for f in ev if f["estrategia"] == est]
            acc = [int(f["aceptadas"]) for f in ff]
            md.append((est, len(ff), ", ".join(map(str, acc)), ff[0]["esperadas"]))
            tex.append((en.get(est, est), len(ff), ", ".join(map(str, acc)), ff[0]["esperadas"]))
            o.macro({"misma_ip": "EvasionSameIp", "sin_cabeceras": "EvasionNoHeaders", "xff_rotada": "EvasionRotatingXff",
                     "bearer_falso": "EvasionFakeBearer"}[est], f"{min(acc)}/{ff[0]['enviadas']}")
        o.texto("\n### Evasión del limitador cambiando la identidad (F-5)\n")
        o.texto("60 peticiones seguidas a /api/execute (límite 30/min) con la compilación sustituida por una respuesta fija. "
                "El limitador identifica al alumno por un `Bearer` o por `X-Forwarded-For` sin comprobar ninguno.\n")
        o.tabla_md(["Estrategia", "Reps", "Aceptadas por prueba", "Esperadas"], md)
        o.latex("evasion", ["Client identity", "Runs", "Accepted", "Limit"], tex,
                "Rate-limiter evasion (finding F-5): 60 back-to-back requests to \\texttt{/api/execute} (limit 30/min). "
                "The limiter keys on client-supplied headers without verifying them." + o.origen_tex(meta_e, "portatil", "seguridad_limitador"),
                alin="lrlr")
        o.fuente(meta_e, "portatil", "seguridad_limitador")

    meta_t, term = cargar("vm", "carga_terminal")
    if term:
        md, tex, peor_p95 = [], [], 0.0
        for k in sorted({int(f["concurrentes"]) for f in term}):
            ff = [f for f in term if int(f["concurrentes"]) == k]
            est = collections.Counter(f["estado"] for f in ff)
            okf = [f for f in ff if f["estado"] == "ok"]
            rp = c.resumen([f["prompt_ms"] for f in okf]) if okf else None
            re_ = c.resumen([f["eco_ms"] for f in okf]) if okf else None
            otros = len(ff) - est["ok"] - est["rechazada_tope"]
            md.append((k, len(ff), est["ok"], est["rechazada_tope"], otros, o.n(rp["mediana"], 0) if rp else "-",
                       o.n(rp["p95"], 0) if rp else "-", o.n(re_["mediana"], 0) if re_ else "-"))
            tex.append((k, len(ff), est["ok"], est["rechazada_tope"], otros, o.n(rp["mediana"], 0) if rp else "--",
                        o.n(rp["p95"], 0) if rp else "--"))
            if k == max(int(f["concurrentes"]) for f in term):
                o.macro("TermLoadMaxConcurrent", str(k))
                o.macro("TermLoadMaxRejected", f"{est['rechazada_tope']}/{len(ff)}")
            if rp and k == 1:
                o.macro("TermOpenMedianMs", o.n(rp["mediana"], 0))
            if rp:
                peor_p95 = max(peor_p95, rp["p95"])
                if k == int(meta_t.get("tope_terminales", 10)):
                    o.macro("TermOpenAtCapMedianMs", o.n(rp["mediana"], 0))
        o.macro("TermOpenWorstPNinetyFiveMs", o.n(peor_p95, 0))
        o.texto("\n### Terminal por WebSocket (2.5.1)\n")
        o.texto(f"Sesiones simultáneas que abren bash, hacen un eco y cierran. Tope configurado: {meta_t.get('tope_terminales', '?')} "
                "terminales. *Apertura*: hasta el primer prompt.\n")
        o.tabla_md(["Simultáneas", "Sesiones", "Correctas", "Rechazadas por el tope", "Otros fallos", "Apertura mediana (ms)",
                    "Apertura p95 (ms)", "Eco mediana (ms)"], md)
        o.latex("loadterm", ["Concurrent", "Sessions", "OK", "Capped", "Failed", "Open median", "Open p95"], tex,
                "Interactive terminal sessions opened at once (time to first shell prompt, ms)."
                + o.origen_tex(meta_t, "vm", "carga_terminal"))
        o.fuente(meta_t, "vm", "carga_terminal")


def objetivos(o):
    """Tabla de objetivos (2.9.3): solo a priori y prerregistrados; los pendientes se dejan como tales."""
    filas_md, filas_tex = [], []
    for clave, es, en, objetivo, origen_obj in OBJETIVOS:
        res, ok = o.cumple.get(clave, ("pendiente" if o.es else "pending", None))
        estado = {True: o.t("sí", "yes"), False: o.t("no", "no"), None: "--" if not o.es else "-"}[ok]
        filas_md.append((es, objetivo, origen_obj, res, estado))
        filas_tex.append((en, objetivo.replace(">=", "$\\geq$").replace("<=", "$\\leq$").replace("±", "$\\pm$").replace("x3", ""),
                          "a priori" if origen_obj == "a priori" else "pre-registered", res, estado))
    o.texto("## Objetivos (registro de decisiones, 2026-11-19)\n")
    o.tabla_md(["Métrica", "Objetivo", "Origen", "Resultado", "¿Cumple?"], filas_md)
    o.latex("targets", ["Metric", "Target", "Set", "Result", "Met"], filas_tex,
            "Targets fixed before measurement (\\emph{a priori}: written before any data; \\emph{pre-registered}: fixed before "
            "that metric was measured). Targets defined after seeing the data are not listed and are not used to claim success.",
            ancha=True, alin="lllll")


def numeros(o):
    lineas = ["% Generado por bench/figuras.py a partir de bench/resultados/: no editar a mano."]
    lineas += [f"\\newcommand{{\\{k}}}{{{v}\\xspace}}" for k, v in sorted(o.num.items())]
    with open(os.path.join(o.gen, "numbers.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


SECCIONES = (sandbox, sobrecoste, terminacion, desconexion, seguridad, seguridad_f3, terminal, terminal_huerfana, docker_bench, corpus, rag, rag_caches, ruteo, ttft, fallback,
             fuga, escaneos, carga, objetivos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=os.path.join(c.BENCH_DIR, "..", "docs", "bench"))
    ap.add_argument("--paper", default=os.path.join(c.BENCH_DIR, "..", "docs", "paper", "latex"))
    a = ap.parse_args()

    es = Salida("es", a.salida)
    es.md = ["# Tablas del banco\n", "Generado por `bench/figuras.py` a partir de `bench/resultados/`. No editar a mano: se sobrescribe.\n"]
    for s in SECCIONES:
        s(es)
    with open(os.path.join(a.salida, "tablas.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(es.md) + "\n")
    print("escrito", os.path.join(a.salida, "tablas.md"), "y", es.figs)

    en = Salida("en", a.paper)
    for s in SECCIONES:
        s(en)
    numeros(en)
    print("escrito", en.gen, "y", en.figs, f"({len(en.num)} macros)")


if __name__ == "__main__":
    main()
