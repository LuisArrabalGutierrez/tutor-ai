
{/* Tipos e interfaces comunes para la aplicación */}

export type Role = 'user' | 'assistant' | 'system';
export type Asignatura = 'cpp' | 'linux';

export interface Message {
  id: string;
  role: Role;
  content: string;
  timestamp: number;
}

{/* Payload para enviar al backend al hacer una consulta al chat, 
  que incluye el historial de mensajes, los archivos del proyecto, 
  la asignatura y el contexto del terminal (si es aplicable) */ }
export interface ChatPayload {
  historial: { role: string; content: string }[];
  archivos: Record<string, string>;
  asignatura: Asignatura;
  terminal_context?: string;
}

{/* Respuesta del backend al hacer una consulta al chat, 
  que incluye la respuesta del asistente y un indicador de si el asistente está escribiendo o no */ }
export interface ExecutePayload {
  archivos: Record<string, string>;
  // Record es un map de clave-valor, donde la clave es un string (nombre del archivo) y el valor es un string (contenido del archivo)
}

{/* Respuesta del backend al ejecutar código, 
  que incluye la salida del terminal y un indicador de si hubo un error o no */ }
export interface ExecuteResponse {
  output: string;
  isError: boolean;
}

// Interfaz para props comunes de componentes
export interface BaseComponentProps {
  className?: string;
}