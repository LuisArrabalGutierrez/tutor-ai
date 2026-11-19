#!/usr/bin/env bash
# Pasos 2.4.7, 2.4.9 y 2.4.10: escaneos con herramientas de terceros. Todas corren en contenedores
# para no instalar nada en la máquina. Los informes en bruto quedan en resultados/escaneos/<entorno>/.
#   bench/seguridad/escaneos.sh [trivy] [gitleaks] [pipaudit] [npmaudit] [zap] [dockerbench]
set -uo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"; BENCH="$(dirname "$AQUI")"; REPO="${BENCH_REPO:-$(dirname "$BENCH")}"
ENTORNO="${BENCH_ENTORNO:-portatil}"
OUT="$BENCH/resultados/escaneos/$ENTORNO"; mkdir -p "$OUT"
FASES="${*:-trivy gitleaks pipaudit npmaudit}"
{ echo "fecha_utc: $(date -u +%FT%TZ)"; echo "entorno: $ENTORNO"; echo "commit: $(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
  echo "imagen_sandbox: $(docker image inspect -f '{{.Id}} creada {{.Created}}' tutor-ugr-image:latest 2>/dev/null)"; } > "$OUT/META.txt"

for fase in $FASES; do case $fase in
  trivy)
    # CVE de la imagen del sandbox y fallos de configuración del Dockerfile
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache aquasec/trivy:0.58.1 \
      image --quiet --scanners vuln --format json tutor-ugr-image:latest > "$OUT/trivy_imagen.json"
    docker run --rm -v "$REPO/backend/docker:/src:ro" -v trivy-cache:/root/.cache aquasec/trivy:0.58.1 \
      config --quiet --format json /src > "$OUT/trivy_dockerfile.json" ;;
  gitleaks)
    docker run --rm -v "$REPO:/repo:ro" zricethezav/gitleaks:v8.21.2 git /repo --redact --no-banner \
      --report-format json --report-path /dev/stdout > "$OUT/gitleaks_historial.json" 2> "$OUT/gitleaks.log" ;;
  pipaudit)
    docker run --rm -v "$REPO/backend:/b:ro" python:3.10-slim sh -c \
      "pip install -q pip-audit >/dev/null 2>&1 && pip-audit -r /b/requirements.lock --no-deps --disable-pip -f json" \
      > "$OUT/pip_audit.json" 2> "$OUT/pip_audit.log" ;;
  npmaudit)
    (cd "$REPO/frontend" && npm audit --json > "$OUT/npm_audit.json" 2> "$OUT/npm_audit.log") ;;
  zap)
    # Contra la instancia de pruebas (LLM simulado) en el puerto 8100 de esta máquina. Nunca contra producción.
    chmod 777 "$OUT"
    docker run --rm --network host -v "$OUT:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
      -t http://127.0.0.1:8100/docs -J zap_baseline.json -I > "$OUT/zap_baseline.log" 2>&1
    docker run --rm --network host -v "$OUT:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py \
      -t http://127.0.0.1:8100/openapi.json -f openapi -J zap_api.json -I > "$OUT/zap_api.log" 2>&1 ;;
  dockerbench)
    # CIS Docker Benchmark. Necesita acceso de lectura a la configuración del demonio.
    docker run --rm --net host --pid host --userns host --cap-add audit_control \
      -v /etc:/etc:ro -v /usr/lib/systemd:/usr/lib/systemd:ro -v /var/lib:/var/lib:ro \
      -v /var/run/docker.sock:/var/run/docker.sock:ro --label docker_bench_security \
      docker/docker-bench-security > "$OUT/docker_bench.log" 2>&1 ;;
esac; echo "$fase hecho"; done
