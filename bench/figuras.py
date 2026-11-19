"""Tablas en Markdown y figuras PNG a partir de los CSV de resultados/.

Solo usa lo que ya está medido; si falta un CSV, esa sección se salta.
Uso: venv/bin/python figuras.py [--salida ../docs/bench]
     escribe <salida>/tablas.md y <salida>/figuras/*.png
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

plt.rcParams.update({
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "text.color": TINTA, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e4e3df", "grid.linewidth": 0.8,
    "font.size": 10, "figure.dpi": 150,
})


def cargar(entorno, nombre):
    ruta = os.path.join(RES, entorno, nombre + ".csv")
    return c.leer_csv(ruta) if os.path.exists(ruta) else (None, None)


def validas(filas):
    return [f for f in filas if f.get("calentamiento", "0") == "0"]


def ms(x):
    return f"{x:,.1f}".replace(",", " ").replace(".", ",")


def tabla(cab, filas):
    out = ["| " + " | ".join(cab) + " |", "| " + " | ".join(":---" if i == 0 else "---:" for i in range(len(cab))) + " |"]
    out += ["| " + " | ".join(str(v) for v in f) + " |" for f in filas]
    return "\n".join(out)


def origen(meta, entorno, nombre):
    return f"*Fuente: `resultados/{entorno}/{nombre}.csv`, {meta.get('fecha_utc', '?')}, commit `{meta.get('commit', '?')[:7]}`, {meta.get('cpu', '?')}.*"


def guardar(fig, carpeta, nombre):
    fig.tight_layout()
    fig.savefig(os.path.join(carpeta, nombre), bbox_inches="tight")
    plt.close(fig)
    return f"![{nombre}](figuras/{nombre})"


def barras_mediana_p95(ax, etiquetas, res, color):
    x = range(len(etiquetas))
    ax.bar(x, [r["mediana"] for r in res], width=0.55, color=color, label="mediana")
    ax.errorbar(x, [r["mediana"] for r in res],
                yerr=[[0] * len(res), [r["p95"] - r["mediana"] for r in res]],
                fmt="none", ecolor=TINTA2, capsize=4, linewidth=1.2, label="hasta p95")
    for i, r in enumerate(res):
        ax.text(i, r["p95"], f" {r['mediana']:.0f}", ha="center", va="bottom", fontsize=9, color=TINTA)
    ax.set_xticks(list(x), etiquetas)


def sandbox(md, figs):
    meta, frio = cargar("vm", "sandbox_frio")
    _, pool = cargar("vm", "sandbox_pool")
    if not frio or not pool:
        return
    frio, pool = validas(frio), validas(pool)
    filas = [("Arranque en frío (`docker run` + `exec`)", c.resumen([f["total_ms"] for f in frio])),
             ("Warm Pool (pedir + `exec`)", c.resumen([f["total_ms"] for f in pool])),
             ("  de ello, `get_container()`", c.resumen([f["get_ms"] for f in pool])),
             ("Reciclado tras usar", c.resumen([f["reciclado_ms"] for f in pool]))]
    md.append("## Sandbox: arranque (2.1.1 a 2.1.3)\n")
    md.append(tabla(["Medida", "n", "Mediana (ms)", "p95 (ms)", "Desv. (ms)"],
                    [(n, r["n"], ms(r["mediana"]), ms(r["p95"]), ms(r["desv"])) for n, r in filas]))
    red = 1 - filas[1][1]["mediana"] / filas[0][1]["mediana"]
    md.append(f"\nReducción de la mediana con el Warm Pool: **{red:.0%}**.\n")
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    barras_mediana_p95(ax, ["Frío", "Warm Pool", "Reciclado"], [filas[0][1], filas[1][1], filas[3][1]], AZUL)
    ax.set_ylabel("ms")
    ax.set_title("Latencia del sandbox en la VM (barra: mediana; bigote: p95)", fontsize=10)
    md.append(guardar(fig, figs, "sandbox_arranque.png"))

    _, raf = cargar("vm", "sandbox_rafagas")
    if raf:
        tam = sorted({int(f["rafaga"]) for f in raf})
        res = [c.resumen([f["espera_ms"] for f in raf if int(f["rafaga"]) == t]) for t in tam]
        md.append("\n### Ráfagas contra un pool de 3 contenedores\n")
        md.append(tabla(["Peticiones a la vez", "n", "Espera mediana (ms)", "p95 (ms)", "Máx. (ms)"],
                        [(t, r["n"], ms(r["mediana"]), ms(r["p95"]), ms(r["max"])) for t, r in zip(tam, res)]))
        fig, ax = plt.subplots(figsize=(5.5, 3.2))
        barras_mediana_p95(ax, [str(t) for t in tam], res, AZUL)
        ax.set_xlabel("peticiones simultáneas")
        ax.set_ylabel("espera por contenedor (ms)")
        ax.set_title("Espera en ráfagas, pool de 3 (barra: mediana; bigote: p95)", fontsize=10)
        md.append("\n" + guardar(fig, figs, "sandbox_rafagas.png"))
    md.append("\n" + origen(meta, "vm", "sandbox_frio") + "\n")


def sobrecoste(md, figs):
    meta, filas = cargar("vm", "sandbox_sobrecoste")
    if not filas:
        return
    filas = validas(filas)
    progs = list(dict.fromkeys(f["programa"] for f in filas))
    r = {(p, v): c.resumen([f["ms"] for f in filas if f["programa"] == p and f["via"] == v]) for p in progs for v in ("host", "sandbox")}
    md.append("## Sandbox: sobrecoste de aislamiento (2.2)\n")
    md.append(tabla(["Programa", "n", "Host mediana (ms)", "Sandbox mediana (ms)", "Diferencia (ms)", "Sandbox / host"],
                    [(p, r[p, "host"]["n"], ms(r[p, "host"]["mediana"]), ms(r[p, "sandbox"]["mediana"]),
                      ms(r[p, "sandbox"]["mediana"] - r[p, "host"]["mediana"]),
                      f"x{r[p, 'sandbox']['mediana'] / r[p, 'host']['mediana']:.2f}".replace(".", ",")) for p in progs]))
    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = range(len(progs))
    ax.bar([i - 0.2 for i in x], [r[p, "host"]["mediana"] for p in progs], width=0.38, color=AZUL, label="host")
    ax.bar([i + 0.2 for i in x], [r[p, "sandbox"]["mediana"] for p in progs], width=0.38, color=NARANJA, label="sandbox")
    ax.set_xticks(list(x), progs)
    ax.set_ylabel("compilar + ejecutar, mediana (ms)")
    ax.set_title("Mismo programa en el host y en el sandbox (VM)", fontsize=10)
    ax.legend(frameon=False)
    md.append("\n" + guardar(fig, figs, "sandbox_sobrecoste.png"))
    md.append("\n" + origen(meta, "vm", "sandbox_sobrecoste") + "\n")


def terminacion(md):
    meta, filas = cargar("vm", "sandbox_terminacion")
    if not filas:
        return
    md.append("## Sandbox: bucle infinito (2.3)\n")
    out = []
    for caso in dict.fromkeys(f["caso"] for f in filas):
        ff = [f for f in filas if f["caso"] == caso]
        r = c.resumen([f["total_ms"] for f in ff])
        recre = sum(f["contenedor_recreado"] == "1" for f in ff)
        restos = sum(int(f["procesos_restantes"] or 0) for f in ff)
        out.append((caso, r["n"], ms(r["mediana"]), ms(r["p95"]), ms(r["max"]),
                    f"{recre} de {len(ff)}" if caso != "referencia" else "-", restos if caso != "referencia" else "-"))
    md.append(tabla(["Caso", "n", "Mediana (ms)", "p95 (ms)", "Máx. (ms)", "Contenedor recreado", "Procesos que quedan"], out))
    md.append("\n" + origen(meta, "vm", "sandbox_terminacion") + "\n")


def seguridad(md, figs):
    meta, filas = cargar("vm", "seguridad_bateria")
    if not filas:
        return
    ataques = list(dict.fromkeys(f["ataque"] for f in filas))
    out, cont = [], []
    for a in ataques:
        ff = [f for f in filas if f["ataque"] == a]
        k = sum(f["contenido"] == "1" for f in ff)
        cont.append((a, k, len(ff)))
        mx = lambda col: max(float(f[col] or 0) for f in ff)  # noqa: E731
        out.append((a, f"{k} de {len(ff)}", ff[0]["mecanismo"], f"{mx('cpu_host_max'):.0f} %", f"{mx('mem_host_caida_mb'):.0f}", f"{mx('cont_pids_max'):.0f}"))
    tot, n = sum(k for _, k, _ in cont), sum(n for *_, n in cont)
    lo, hi = c.wilson(tot, n)
    md.append("## Seguridad: batería de ataques contra el Warm Pool (2.4.2, 2.4.3)\n")
    md.append(tabla(["Ataque", "Contenido", "Qué lo para", "CPU host máx.", "Caída RAM host máx. (MB)", "PIDs máx. en el contenedor"], out))
    md.append(f"\nTasa de contención: **{tot} de {n} ({tot / n:.0%})**, intervalo de Wilson al 95 %: {lo:.0%} a {hi:.0%}.\n")
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    y = range(len(cont))
    ax.barh(list(y), [k for _, k, _ in cont], color=AZUL, height=0.6, label="contenido")
    ax.barh(list(y), [n - k for _, k, n in cont], left=[k for _, k, _ in cont], color=NARANJA, height=0.6, label="no contenido")
    ax.set_yticks(list(y), [a for a, *_ in cont])
    ax.invert_yaxis()
    ax.set_xlabel("repeticiones")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Ataques contenidos en la VM: {tot} de {n}", fontsize=10)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    md.append(guardar(fig, figs, "seguridad_contencion.png"))
    md.append("\n" + origen(meta, "vm", "seguridad_bateria") + "\n")


def rag(md, figs):
    meta, filas = cargar("portatil", "rag_metricas")
    if not filas:
        return
    sel = [f for f in filas if f["criterio"] in ("estricto", "mas_menos_1") and f["umbral"] == "0.4"]
    md.append("## RAG: calidad de recuperación (2.6)\n")
    md.append("Umbral de producción 0,40. *Estricto*: la diapositiva etiquetada; *±1*: también la anterior o la siguiente.\n")
    md.append(tabla(["Grupo", "Criterio", "n", "Recall@1", "Recall@3", "Recall@5", "MRR", "Top-1 de otra asignatura", "Alguna de otra asignatura en top-5"],
                    [(f["valor"], f["criterio"].replace("mas_menos_1", "±1"), f["n"], f["recall@1"], f["recall@3"], f["recall@5"], f["mrr"],
                      f["top1_otra_asignatura"] or "-", f["alguna_otra_asignatura"] or "-") for f in sel]))
    umb = [f for f in filas if f["valor"] == "todas" and f["criterio"] == "estricto"]
    md.append("\nEfecto del umbral (total, estricto):\n")
    md.append(tabla(["Umbral", "Recall@1", "Recall@5", "Sin resultado"], [(f["umbral"], f["recall@1"], f["recall@5"], f["sin_resultado"]) for f in umb]))
    grupos = [f for f in sel if f["criterio"] == "estricto"]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = range(len(grupos))
    for j, (k, col) in enumerate((("recall@1", AZUL), ("recall@3", NARANJA), ("recall@5", AQUA))):
        ax.bar([i + (j - 1) * 0.26 for i in x], [float(f[k]) for f in grupos], width=0.25, color=col, label=k.replace("recall", "Recall"))
    ax.set_xticks(list(x), [f["valor"] for f in grupos])
    ax.axvline(3.5, color=TINTA2, linewidth=0.8, linestyle=":")
    ax.set_ylim(0, 1.05)
    ax.set_title("Recall@K por asignatura y por tipo de pregunta (estricto, umbral 0,40)", fontsize=10)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    md.append("\n" + guardar(fig, figs, "rag_recall.png"))
    md.append("\n" + origen(meta, "portatil", "rag_metricas") + "\n")


def ruteo(md, figs):
    meta, filas = cargar("portatil", "tutor_ruteo")
    if not filas:
        return
    cls = ["ninguna", "apuntes", "compilar", "internet"]
    m = collections.Counter((f["esperada"], f["primera"]) for f in filas)
    ok = sum(f["acierto_primera"] == "1" for f in filas)
    md.append("## Tutor: ruteo de herramientas (2.7.1 a 2.7.3)\n")
    md.append(f"Acierto con la primera herramienta: **{ok} de {len(filas)}**; con la esperada en alguna llamada: {sum(f['acierto_incluida'] == '1' for f in filas)} de {len(filas)}.\n")
    md.append("Matriz de confusión (filas: esperada; columnas: primera herramienta usada):\n")
    md.append(tabla(["Esperada \\ usada"] + cls, [[e] + [m[e, u] for u in cls] for e in cls]))
    fig, ax = plt.subplots(figsize=(4.4, 3.6))
    datos = [[m[e, u] for u in cls] for e in cls]
    ax.imshow(datos, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("azul", ["#f1f6fd", "#184f95"]))
    for i in range(4):
        for j in range(4):
            v = datos[i][j]
            ax.text(j, i, v, ha="center", va="center", color="white" if v > 8 else TINTA, fontsize=10)
    ax.set_xticks(range(4), cls)
    ax.set_yticks(range(4), cls)
    ax.set_xlabel("primera herramienta usada")
    ax.set_ylabel("esperada")
    ax.grid(False)
    ax.set_title(f"Ruteo del tutor: {ok} de {len(filas)} aciertos", fontsize=10)
    md.append("\n" + guardar(fig, figs, "tutor_ruteo.png"))
    md.append("\n" + origen(meta, "portatil", "tutor_ruteo") + "\n")


def escaneos(md):
    meta, filas = cargar("portatil", "escaneos_resumen")
    if not filas:
        return
    md.append("## Escaneos de imagen, dependencias y secretos (2.4.9)\n")
    md.append(tabla(["Herramienta", "Objetivo", "Gravedad", "Hallazgos", "Con arreglo publicado", "Dónde"],
                    [(f["herramienta"], f["objetivo"], f["gravedad"], f["hallazgos"], f["con_arreglo"] or "-", f["detalle"] or "-") for f in filas]))
    md.append("\n" + origen(meta, "portatil", "escaneos_resumen") + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=os.path.join(c.BENCH_DIR, "..", "docs", "bench"))
    a = ap.parse_args()
    figs = os.path.join(a.salida, "figuras")
    os.makedirs(figs, exist_ok=True)
    md = ["# Tablas del banco\n", "Generado por `bench/figuras.py` a partir de `bench/resultados/`. No editar a mano: se sobrescribe.\n"]
    sandbox(md, figs)
    sobrecoste(md, figs)
    terminacion(md)
    seguridad(md, figs)
    rag(md, figs)
    ruteo(md, figs)
    escaneos(md)
    with open(os.path.join(a.salida, "tablas.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("escrito", os.path.join(a.salida, "tablas.md"), "y", figs)


if __name__ == "__main__":
    main()
