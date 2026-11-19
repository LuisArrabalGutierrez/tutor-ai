# bench/

Banco de pruebas del artículo de TutorIA. Cada medida tiene un script, deja un CSV con una fila por medida y sus metadatos (fecha, commit, máquina, versiones), y las tablas y figuras salen de esos CSV con un solo comando.

## Reglas

- Ningún número se copia a mano: todo sale de `resultados/` con `generar_tablas.py`.
- Las latencias se repiten 30 veces o más. Se publica mediana, p95 y desviación. Las repeticiones de calentamiento que se descartan van marcadas en el propio CSV (`calentamiento=1`).
- Los resultados malos se quedan.
- Producción no se ataca. La carga y el escaneo de la API van contra una segunda instancia (`carga/servidor_mock.py`) con un pool de contenedores propio (`bench_api_*`) y el LLM simulado.

## Entornos

`BENCH_ENTORNO` decide la carpeta de salida: `resultados/vm/` para la VM de producción (los números del artículo) y `resultados/portatil/` para el portátil (pruebas de los scripts y medidas que no dependen de la máquina, como la calidad del RAG).

| Variable | Para qué | Por defecto |
| :--- | :--- | :--- |
| `BENCH_ENTORNO` | Carpeta de resultados | `portatil` |
| `BENCH_BACKEND` | Ruta del backend que se importa | `../backend` |
| `BENCH_COMMIT` | Commit que se anota en el CSV | `git rev-parse HEAD` del backend |

En la VM el banco se copia a `~/tutor-ai-bench`, fuera del repositorio desplegado, con `./vm.sh subir`.

## Preparación

```bash
# Dependencias del backend (las mismas que en producción)
python3 -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.lock
# Solo para generar las figuras
python3 -m venv bench/venv && bench/venv/bin/pip install -r bench/requirements.txt
# Imagen del sandbox
docker build -t tutor-ugr-image backend/docker
```

Hace falta Docker, k6 para la carga y, para los escaneos, salida a internet para descargar las imágenes de las herramientas.

## Cómo repetir cada medida

`PY` es el Python del backend (`backend/venv/bin/python`). Las órdenes se lanzan desde `bench/`.

| Paso del plan | Qué mide | Orden | CSV |
| :--- | :--- | :--- | :--- |
| 2.1 | Arranque en frío, Warm Pool, reciclado y ráfagas | `$PY sandbox/arranque.py todo` | `sandbox_frio`, `sandbox_pool`, `sandbox_rafagas` |
| 2.2 | Sobrecoste frente a compilar en la máquina | `$PY sandbox/sobrecoste.py` | `sandbox_sobrecoste` |
| 2.3 | Bucle infinito: tiempo hasta responder y limpieza | `$PY sandbox/terminacion.py` | `sandbox_terminacion` |
| 2.4.1 a 2.4.6 | Batería de ataques contra el Warm Pool | `$PY seguridad/bateria.py` | `seguridad_bateria` |
| 2.4.4 | Ataques contra la terminal | `$PY seguridad/terminal.py --url ws://127.0.0.1:8100` | `seguridad_terminal` |
| 2.4.7, 2.4.9, 2.4.10 | ZAP, Trivy, gitleaks, pip-audit, npm audit, docker-bench | `seguridad/escaneos.sh` y `$PY seguridad/resumen_escaneos.py` | `escaneos_resumen` e informes en `resultados/escaneos/` |
| 2.5 | Carga, rampa, pico, limitador y terminal | `carga/sesion.sh` (desde el portátil, contra la VM) | `carga_execute`, `carga_chat`, `carga_rate_limit`, `carga_terminal`, `monitor_*` |
| 2.6.4 a 2.6.7 | Recuperación del RAG | `$PY rag/evaluar.py` y `$PY rag/metricas.py` | `rag_resultados`, `rag_metricas` |
| 2.6.8 | Cachés del RAG | `$PY rag/caches.py` | `rag_caches` |
| 2.7.1 a 2.7.3, 2.7.6 | Ruteo de herramientas y formato | `cd tutor && $PY ruteo.py` | `tutor_ruteo` |
| 2.7.4 | TTFT por SSE | `$PY tutor/ttft.py --url http://127.0.0.1:8000` | `tutor_ttft` |
| 2.7.5 | Caída de Gemini | `cd tutor && $PY fallback.py normal && $PY fallback.py gemini_caida` | `tutor_fallback` |
| 2.8 | Fuga de solución con y sin guardrail | `cd tutor && TUTOR_GRAPH=1 $PY fuga.py && TUTOR_GRAPH=0 $PY fuga.py && $PY juez.py juzgar` | `tutor_fuga_*` |
| 2.1.5, 2.2.4, 2.4.6, 2.7.3 | Tablas en Markdown y figuras PNG de lo ya medido | `venv/bin/python figuras.py [--salida DIR]` | `DIR/tablas.md`, `DIR/figuras/` (por defecto `../docs/bench/`) |
| 2.9 | Tablas y figuras | `venv/bin/python generar_tablas.py` | `resultados/tablas/`, `resultados/figuras/` |

Las medidas con LLM real (`ruteo`, `ttft`, `fallback`, `fuga`, `juez`) gastan cuota. Son reanudables: si la cuota se agota se paran, y al relanzarlas siguen donde iban. No se pueden lanzar dos a la vez, porque comparten los contenedores `tutor_mcp_*`.

## Qué se publica y qué no

- `rag/preguntas.csv`: preguntas propias con el nombre del PDF y el número de diapositiva. No lleva texto de los apuntes.
- Las respuestas completas del tutor pueden citar fragmentos de los apuntes. Se guardan fuera del repositorio, en `docs/bench/tutor/*.jsonl`; en `resultados/` solo van las métricas.
- Sin acceso a los apuntes y a la base de datos del autor, la evaluación del RAG no se puede repetir. El resto sí.

## Hallazgos del banco

Fallos del sistema que salieron al medir. Los dos primeros están corregidos después de la versión medida (`v1.0-paper-baseline`), con test de regresión en `backend/tests/test_compiler_robustez.py`.

| Id | Qué pasa | Cómo se vio | Estado |
| :--- | :--- | :--- | :--- |
| F-1 | En la VM, `docker cp` deja los archivos del proyecto con el uid del usuario de la máquina (1002) y dentro del contenedor manda `alumno` (1000). El alumno no puede escribir en las subcarpetas ni modificar sus archivos: un Makefile que deja los `.o` en `src/` falla con *Permission denied*. En el portátil no ocurre, porque los dos uid son 1000. | `sandbox/sobrecoste.py` en la VM | Corregido: el proyecto se vuelca con `tar` por stdin |
| F-2 | Si un programa inunda la salida, la API corta a los 64 KB y mata al cliente de Docker. Si otro proceso sigue escribiendo en la tubería, `asyncio` la pausa con el búfer lleno, nunca lee el final y la petición no vuelve. El contenedor no regresa al pool. | `seguridad/bateria.py`, ataque `salida`, de forma intermitente | Corregido: la tubería se vacía hasta el final antes de esperar al proceso |
| F-3 | El sandbox no limita el disco: un programa escribe 1 GiB en `/tmp` sin que nada lo pare. El espacio se libera al reciclar el contenedor. | `seguridad/bateria.py`, ataques `disco_tmp` y `disco_cwd` | Abierto (ver el artículo, riesgos aceptados) |
