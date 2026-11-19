#!/usr/bin/env bash
# Lanza una medida en la VM y trae los resultados. Requiere el alias SSH `tutoria-vm`.
#   bench/vm.sh subir                      copia bench/ a ~/tutor-ai-bench en la VM
#   bench/vm.sh lanzar <nombre> <orden>    ejecuta la orden con nohup; log en logs/<nombre>.log
#   bench/vm.sh estado <nombre>            últimas líneas del log y si sigue vivo
#   bench/vm.sh traer                      copia resultados/vm al portátil
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -o BatchMode=yes -o User="${VM_USER:-luisarrabalgutierrez}" tutoria-vm)
DEST='~/tutor-ai-bench'
case "${1:-}" in
  subir)
    rsync -az --delete --exclude venv --exclude 'resultados/' --exclude '__pycache__' --exclude logs \
      -e "ssh -o BatchMode=yes -o User=${VM_USER:-luisarrabalgutierrez}" "$AQUI/" "tutoria-vm:tutor-ai-bench/" ;;
  lanzar)
    nombre="$2"; shift 2
    "${SSH[@]}" "mkdir -p $DEST/logs && cd $DEST && BENCH_ENTORNO=vm BENCH_BACKEND=\$HOME/tutor-ai/backend PY=\$HOME/tutor-ai/backend/venv/bin/python nohup bash -c '$*' > logs/$nombre.log 2>&1 < /dev/null & echo lanzado" ;;
  estado)
    "${SSH[@]}" "tail -n ${3:-8} $DEST/logs/$2.log; pgrep -af 'tutor-ai-bench|bench/' | grep -v pgrep | cut -c1-120 || echo '(sin procesos del banco)'" ;;
  traer)
    mkdir -p "$AQUI/resultados/vm"
    rsync -az -e "ssh -o BatchMode=yes -o User=${VM_USER:-luisarrabalgutierrez}" "tutoria-vm:tutor-ai-bench/resultados/vm/" "$AQUI/resultados/vm/" ;;
  *) sed -n 2,7p "$0" ;;
esac
