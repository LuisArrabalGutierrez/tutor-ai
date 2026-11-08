# Frontend de TutorIA

Interfaz web del tutor: editor Monaco, consola de C++, terminal Linux (xterm.js) y chat con el tutor socrático.

React 19 + TypeScript + Vite 7 + Tailwind 4. La visión general del proyecto y la arquitectura están en el [README de la raíz](../README.md) y en [`docs/EXPLICACION.md`](../docs/EXPLICACION.md).

## Arranque

```bash
cp .env.example .env     # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY y VITE_GOOGLE_IP
npm install
npm run dev              # http://localhost:5173 (proxy de /api a http://localhost:8000)
```

Scripts: `npm run build` (`tsc -b` y `vite build`), `npm run lint` (ESLint). La integración continua ejecuta los dos.

## Estructura de `src/`

| Ruta | Qué contiene |
| :--- | :--- |
| `App.tsx` | Diseño, selector de asignatura (C/C++ o Linux) y sesión de Supabase |
| `hooks/` | `useProject` (archivos en `localStorage`), `UseChat` (chat por SSE), `useTerminal` (ejecución de C++) |
| `services/api.ts` | Cliente HTTP: chat en streaming con respaldo y ejecución con timeout |
| `lib/supabase.ts`, `lib/tutorLinks.ts` | Cliente de Supabase; normalización de enlaces del tutor y detección de la cita oficial |
| `components/` | `auth`, `chat`, `editor` (Monaco, árbol de archivos, consola, terminal Linux) y `layout` |

## Variables de entorno

| Variable | Uso |
| :--- | :--- |
| `VITE_API_URL` | URL del backend; solo se usa en `localhost` (en producción las peticiones van por el rewrite de `vercel.json`) |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Cliente de Supabase en el navegador |
| `VITE_GOOGLE_IP` | Host del WebSocket de la terminal en producción (dominio de ngrok); se convierte a `wss://` |
