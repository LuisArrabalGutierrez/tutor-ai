import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

/**
 * Obtiene la URL del WebSocket de la terminal.
 * En local usa ws://localhost:8000/ws/terminal.
 * En producción (HTTPS) usa un túnel seguro con certificado SSL (wss://) para evitar errores de Mixed Content.
 */
function getSocketUrl(): string {
  const isLocal = typeof window !== 'undefined' && 
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");

  if (isLocal) {
    return 'ws://localhost:8000/ws/terminal';
  }

  const rawHost = import.meta.env.VITE_GOOGLE_IP?.trim() || '';

  if (!rawHost) {
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' && window.location.host ? window.location.host : 'localhost:8000';
    return `${protocol}//${host}/ws/terminal`;
  }

  // Si ya contiene protocolo ws:// o wss://
  if (rawHost.startsWith('wss://') || rawHost.startsWith('ws://')) {
    const trimmed = rawHost.replace(/\/+$/, '');
    return trimmed.endsWith('/ws/terminal') ? trimmed : `${trimmed}/ws/terminal`;
  }

  // Si contiene http:// o https://
  if (rawHost.startsWith('http://') || rawHost.startsWith('https://')) {
    const cleanHost = rawHost.replace(/^https?:\/\//, '').replace(/\/+$/, '');
    return cleanHost.endsWith('/ws/terminal') ? `wss://${cleanHost}` : `wss://${cleanHost}/ws/terminal`;
  }

  // Dominio o IP directo (ej. lunar-finicky-concierge.ngrok-free.dev)
  const cleanHost = rawHost.replace(/\/+$/, '');
  return cleanHost.endsWith('/ws/terminal') ? `wss://${cleanHost}` : `wss://${cleanHost}/ws/terminal`;
}

const MAX_HISTORY_CHARS = 2000;
const FLUSH_INTERVAL_MS = 250;

// Quita secuencias de color/cursor de xterm y retornos de carro para que el LLM lea texto plano
// eslint-disable-next-line no-control-regex
const ANSI_PATTERN = /\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\r/g;
const stripAnsi = (text: string): string => text.replace(ANSI_PATTERN, '');

interface LinuxTerminalProps {
  onTerminalOutputChange?: (output: string) => void;
}

export default function LinuxTerminal({ onTerminalOutputChange }: LinuxTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const outputHistory = useRef<string>("");

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      theme: { 
        background: '#1e1e1e',
        foreground: '#cccccc',
        cursor: '#ffffff'
      },
      cursorBlink: true,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14,
    });
    
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    
    term.open(terminalRef.current);
    fitAddon.fit();
    termRef.current = term;

    term.writeln('\x1b[33m[Conectando con el entorno Linux UGR...]\x1b[0m');

    const socketUrl = getSocketUrl();
    let flushTimer: number | null = null;

    // Conexión WebSocket
    const ws = new WebSocket(socketUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      term.clear();
      term.writeln('\x1b[32;1m[Conexión establecida con el servidor Linux de la UGR]\x1b[0m\r\n');
      // Sincronizar dimensiones iniciales de la ventana con el PTY del backend (TIOCSWINSZ)
      try {
        fitAddon.fit();
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      } catch {
        // Fallback si aún no tiene dimensiones finales
      }
    };

    ws.onerror = () => {
      term.writeln('\r\n\x1b[31;1m[Error de conexión con el WebSocket de la terminal]\x1b[0m');
      term.writeln(`\x1b[33mNo se pudo conectar a: ${socketUrl}\x1b[0m`);
      term.writeln('\x1b[90mEn producción HTTPS, la terminal requiere un túnel seguro WSS activo (ej. Ngrok / Cloudflare Tunnel).\x1b[0m\r\n');
    };

    ws.onclose = (event) => {
      if (!event.wasClean) {
        term.writeln('\r\n\x1b[31m[Conexión cerrada por el servidor]\x1b[0m\r\n');
      }
    };

    // Renderiza salida del servidor y acumula el historial que se envía al tutor como contexto
    ws.onmessage = (event) => {
      term.write(event.data);

      outputHistory.current = (outputHistory.current + stripAnsi(event.data)).slice(-MAX_HISTORY_CHARS);

      // Throttle: un `cat` grande no debe re-renderizar la app en cada paquete
      if (onTerminalOutputChange && flushTimer === null) {
        flushTimer = window.setTimeout(() => {
          flushTimer = null;
          onTerminalOutputChange(outputHistory.current);
        }, FLUSH_INTERVAL_MS);
      }
    };

    // Envía input al servidor
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    // Escucha eventos de redimensionado de xterm (provocados por fitAddon) y los envía al backend
    const resizeDisposable = term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });

    // Redimensionado de terminal ante cambios de tamaño de ventana o split panels
    const handleResize = () => {
      try {
        fitAddon.fit();
      } catch {
        // Ignora si el elemento no es visible
      }
    };
    window.addEventListener('resize', handleResize);

    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
      } catch {
        // Ignora errores si está oculto
      }
    });
    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current);
    }

    // Cleanup
    return () => {
      if (flushTimer !== null) window.clearTimeout(flushTimer);
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      resizeDisposable.dispose();
      ws.close();
      term.dispose();
    };
  }, [onTerminalOutputChange]);

  return (
    <div className="w-full h-full bg-[#1e1e1e] p-2 overflow-hidden">
      <div ref={terminalRef} className="w-full h-full" />
    </div>
  );
}