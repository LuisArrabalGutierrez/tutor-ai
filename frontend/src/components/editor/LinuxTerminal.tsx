import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const GOOGLE_IP = import.meta.env.VITE_GOOGLE_IP;

// Si es local usa ws y puerto 8000. Si es ngrok usa wss sin puerto.
const socketUrl = isLocal 
  ? `ws://localhost:8000/ws/terminal` 
  : `wss://${GOOGLE_IP}/ws/terminal`;

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

    // Conexión WebSocket
    const ws = new WebSocket(socketUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      term.writeln('\x1b[32;1m[Conexión establecida con el servidor Linux de la UGR]\x1b[0m\r\n');
    };

    // Renderiza salida del servidor y actualiza el historial
    ws.onmessage = (event) => {
      term.write(event.data);


      // Limita el historial a 2000 caracteres
      if (outputHistory.current.length > 2000) {
        outputHistory.current = outputHistory.current.slice(-2000);
      }

      // Emite el cambio al componente padre
      if (onTerminalOutputChange) {
        onTerminalOutputChange(outputHistory.current);
      }
    };

    // Envía input al servidor
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    // Redimensionado de terminal
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
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