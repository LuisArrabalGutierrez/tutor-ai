#!/usr/bin/env bash
# Sesión completa de carga (pasos 2.5.1 a 2.5.8). Se lanza desde el portátil: el servidor de pruebas corre
# en la VM y los clientes (k6 y Python) aquí, por un túnel SSH al puerto 8100.
#   bench/carga/sesion.sh [execute] [chat] [rampa] [pico] [limite] [terminal]   (sin argumentos: todo)
set -uo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"; BENCH="$(dirname "$AQUI")"
PY="${PY:-$BENCH/../backend/venv/bin/python}"
SSH=(ssh -o BatchMode=yes -o User=luisarrabalgutierrez tutoria-vm)
export BENCH_ENTORNO=vm BENCH_COMMIT="${BENCH_COMMIT:-$("${SSH[@]}" 'git -C tutor-ai rev-parse HEAD')}"
URL=http://127.0.0.1:8100
RES="$BENCH/resultados/vm"; mkdir -p "$RES"
FASES="${*:-execute chat rampa pico limite terminal}"

"$BENCH/vm.sh" subir
"$BENCH/vm.sh" lanzar api '$PY carga/servidor_mock.py --port 8100'
"$BENCH/vm.sh" lanzar monitor "\$PY carga/monitor.py --etiqueta carga_$(date +%d_%H%M) --segundos 14400"
"${SSH[@]}" -o ExitOnForwardFailure=yes -N -L 8100:127.0.0.1:8100 &
TUNEL=$!
# El patrón con corchete evita que pkill -f se encuentre a sí mismo
limpiar() { kill $TUNEL 2>/dev/null; "${SSH[@]}" "pkill -f '[s]ervidor_mock.py'; pkill -f '[c]arga/monitor.py'; sleep 3; docker ps -aq --filter name=bench_api_ | xargs -r docker rm -f" >/dev/null 2>&1; "$BENCH/vm.sh" traer; }
trap limpiar EXIT
for i in $(seq 40); do curl -s -o /dev/null "$URL/docs" && break; sleep 2; done

# k6 guarda una línea por métrica; aquí se queda solo con las dos propias y se le añaden las columnas del nivel
k6_a_csv() {  # modo vus rep [duracion]
  local bruto; bruto="$(mktemp)"
  k6 run -q -e URL=$URL -e MODO="$1" -e VUS="$2" -e DURACION="${4:-180s}" --out csv="$bruto" "$AQUI/execute.js" > /dev/null 2>&1
  local destino="$RES/carga_execute.csv"
  if [ ! -f "$destino" ]; then
    { echo "# fecha_utc: $(date -u +%FT%TZ)"; echo "# entorno: vm"; echo "# commit: $BENCH_COMMIT"
      echo "# cliente: k6 $(k6 version | cut -d' ' -f2) en el portatil, por tunel SSH"
      echo "# pausa_entre_peticiones_s: 2.5"; echo "modo,vus,rep,metrica,epoch_s,ms,resultado"; } > "$destino"
  fi
  awk -F, -v m="$1" -v v="$2" -v r="$3" '$1=="exec_ms"||$1=="docs_ms"{sub("resultado=","",$18); printf "%s,%s,%s,%s,%s,%.2f,%s\n", m,v,r,$1,$2,$3,$18}' "$bruto" >> "$destino"
  rm -f "$bruto"
}

for fase in $FASES; do case $fase in
  execute) for vus in 10 50 100; do for rep in 1 2 3; do echo "execute $vus rep $rep"; k6_a_csv constante $vus $rep; sleep 70; done; done ;;
  chat)    for vus in 10 50 100; do for rep in 1 2 3; do echo "chat $vus rep $rep"; "$PY" "$AQUI/chat_sse.py" --url $URL --clientes $vus --duracion 180 --rep $rep; sleep 70; done; done ;;
  rampa)   echo rampa; k6_a_csv rampa 100 1 300s; sleep 70 ;;
  pico)    echo pico; k6_a_csv pico 100 1; sleep 70 ;;
  limite)  echo limite; "$PY" "$AQUI/rate_limit.py" --url $URL --reps 3 ;;
  terminal) echo terminal; "$PY" "$AQUI/terminal_ws.py" --url ws://127.0.0.1:8100 ;;
esac; done
