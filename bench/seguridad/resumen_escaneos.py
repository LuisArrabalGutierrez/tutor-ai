"""Resume los informes de `escaneos.sh` en un CSV (pasos 2.4.7, 2.4.9 y 2.4.10).

El JSON de Trivy pesa decenas de MB: se sustituye por una versión reducida (CVE, paquete, gravedad, arreglo).
Uso: python bench/seguridad/resumen_escaneos.py
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common as c

DIR = os.path.join(c.BENCH_DIR, "resultados", "escaneos", c.ENTORNO)


def cargar(nombre: str):
    ruta = os.path.join(DIR, nombre)
    if not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    out = c.Csv("escaneos_resumen", ["herramienta", "objetivo", "gravedad", "hallazgos", "con_arreglo", "detalle"],
                {"informes": f"resultados/escaneos/{c.ENTORNO}/"})
    t = cargar("trivy_imagen.json")
    if t is not None:
        vulns = [v for r in t.get("Results", []) for v in (r.get("Vulnerabilities") or [])] if "Results" in t else t
        reducido = [{"id": v.get("VulnerabilityID", v.get("id")), "paquete": v.get("PkgName", v.get("paquete")),
                     "gravedad": v.get("Severity", v.get("gravedad")), "arreglo": v.get("FixedVersion", v.get("arreglo", ""))}
                    for v in vulns]
        with open(os.path.join(DIR, "trivy_imagen.json"), "w", encoding="utf-8") as f:
            json.dump(reducido, f)
        unicos = {(v["id"], v["paquete"]): v for v in reducido}.values()
        for g in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"):
            sel = [v for v in unicos if v["gravedad"] == g]
            if sel:
                top = collections.Counter(v["paquete"] for v in sel).most_common(3)
                out.fila(herramienta="trivy", objetivo="imagen tutor-ugr-image", gravedad=g, hallazgos=len(sel),
                         con_arreglo=sum(1 for v in sel if v["arreglo"]), detalle="; ".join(f"{p} ({n})" for p, n in top))
    t = cargar("trivy_dockerfile.json")
    if t is not None:
        for r in t.get("Results", []):
            for m in r.get("Misconfigurations") or []:
                out.fila(herramienta="trivy config", objetivo="Dockerfile del sandbox", gravedad=m["Severity"], hallazgos=1,
                         detalle=f"{m['ID']}: {m['Title']}")
    g = cargar("gitleaks_historial.json")
    if g is not None:
        out.fila(herramienta="gitleaks", objetivo="historial de Git", gravedad="secreto", hallazgos=len(g),
                 detalle="; ".join(sorted({x.get("RuleID", "") for x in g}))[:150])
    p = cargar("pip_audit.json")
    if p is not None:
        con = [d for d in p["dependencies"] if d.get("vulns")]
        out.fila(herramienta="pip-audit", objetivo="backend/requirements.lock", gravedad="aviso",
                 hallazgos=sum(len({v["id"] for v in d["vulns"]}) for d in con),
                 con_arreglo=sum(len({v["id"] for v in d["vulns"] if v.get("fix_versions")}) for d in con),
                 detalle="; ".join(f"{d['name']} {d['version']} ({len({v['id'] for v in d['vulns']})})" for d in con))
    n = cargar("npm_audit.json")
    if n is not None:
        for g_, k in n.get("metadata", {}).get("vulnerabilities", {}).items():
            if g_ not in ("info", "total") and k:
                nombres = [nom for nom, v in n.get("vulnerabilities", {}).items() if v.get("severity") == g_]
                out.fila(herramienta="npm audit", objetivo="frontend", gravedad=g_, hallazgos=k,
                         con_arreglo=sum(1 for nom in nombres if n["vulnerabilities"][nom].get("fixAvailable")),
                         detalle=", ".join(nombres[:6]))
    for nombre, etiqueta in (("zap_baseline.json", "ZAP baseline"), ("zap_api.json", "ZAP API scan")):
        z = cargar(nombre)
        if z is not None:
            alertas = [a for s in z.get("site", []) for a in s.get("alerts", [])]
            for riesgo in ("High", "Medium", "Low", "Informational"):
                sel = [a for a in alertas if a.get("riskdesc", "").startswith(riesgo)]
                if sel:
                    out.fila(herramienta=etiqueta, objetivo="API de pruebas (LLM simulado)", gravedad=riesgo, hallazgos=len(sel),
                             detalle="; ".join(a["name"] for a in sel)[:300])
    ruta = os.path.join(DIR, "docker_bench.log")
    if os.path.exists(ruta):
        texto = re.sub(r"\x1b\[[0-9;]*m", "", open(ruta, encoding="utf-8", errors="replace").read())
        for nivel in ("PASS", "WARN", "INFO", "NOTE"):
            lineas = re.findall(rf"^\[{nivel}\]\s+(\d+\.\d+(?:\.\d+)?)\s", texto, re.M)
            if lineas:
                out.fila(herramienta="docker-bench-security", objetivo="demonio y contenedores", gravedad=nivel,
                         hallazgos=len(lineas), detalle=" ".join(lineas)[:300] if nivel == "WARN" else "")
    out.cerrar()
    with open(out.ruta, encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    main()
