// k6: carga sobre /api/execute, con una sonda a /docs en paralelo (paso 2.5.6).
//   k6 run -e URL=http://127.0.0.1:8100 -e MODO=constante -e VUS=10 -e DURACION=180s --out csv=x.csv execute.js
// MODO: constante | rampa (0 a VUS en DURACION) | pico (0 a VUS de golpe 60 s, y después 120 s de recuperación)
import http from 'k6/http';
import { sleep } from 'k6';
import { Trend } from 'k6/metrics';

const URL = __ENV.URL || 'http://127.0.0.1:8100';
const VUS = parseInt(__ENV.VUS || '10');
const DURACION = __ENV.DURACION || '180s';
const MODO = __ENV.MODO || 'constante';
// Cada cliente manda una compilación cada 2,5 s: 24 por minuto, bajo el límite de 30 por minuto
const PAUSA_S = parseFloat(__ENV.PAUSA_S || '2.5');

const exec_ms = new Trend('exec_ms', true);
const docs_ms = new Trend('docs_ms', true);

const carga = {
  constante: { executor: 'constant-vus', vus: VUS, duration: DURACION },
  rampa: { executor: 'ramping-vus', startVUs: 0, stages: [{ duration: DURACION, target: VUS }], gracefulRampDown: '40s' },
  pico: { executor: 'ramping-vus', startVUs: 0, stages: [{ duration: '1s', target: VUS }, { duration: '60s', target: VUS }, { duration: '1s', target: 0 }], gracefulRampDown: '40s' },
}[MODO];

export const options = {
  scenarios: {
    compilar: Object.assign({ exec: 'compilar', gracefulStop: '40s' }, carga),
    sonda: { executor: 'constant-vus', vus: 1, duration: MODO === 'pico' ? '182s' : DURACION, exec: 'sonda' },
  },
  summaryTrendStats: ['med', 'p(95)', 'p(99)', 'max'],
};

const PROGRAMA = JSON.stringify({
  archivos: { 'main.cpp': '#include <iostream>\nint main() { int s = 0; for (int i = 0; i < 1000; ++i) s += i; std::cout << s << std::endl; return 0; }\n' },
});

export function compilar() {
  // Un identificador por cliente virtual: el limitador cuenta por alumno, no por la IP del túnel
  const cabeceras = { 'Content-Type': 'application/json', 'X-Forwarded-For': `10.9.${Math.floor(__VU / 250)}.${__VU % 250}` };
  const r = http.post(`${URL}/api/execute`, PROGRAMA, { headers: cabeceras, timeout: '70s' });
  let resultado = 'error_http';
  if (r.status === 429) resultado = 'limite_429';
  else if (r.status >= 500) resultado = 'error_5xx';
  else if (r.status === 200) {
    const cuerpo = r.json();
    if (!cuerpo.isError) resultado = 'ok';
    else if (String(cuerpo.output).includes('ocupado')) resultado = 'pool_ocupado';
    else resultado = 'error_ejecucion';
  } else if (r.status === 0) resultado = 'sin_respuesta';
  exec_ms.add(r.timings.duration, { resultado: resultado });
  sleep(PAUSA_S);
}

export function sonda() {
  const r = http.get(`${URL}/docs`, { headers: { 'X-Forwarded-For': '10.8.0.1' }, timeout: '30s' });
  docs_ms.add(r.timings.duration, { resultado: r.status === 200 ? 'ok' : `http_${r.status}` });
  sleep(1);
}
