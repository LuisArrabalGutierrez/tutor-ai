
export type Role = 'user' | 'assistant' | 'system';
export type Asignatura = 'cpp' | 'linux';

export interface Message {
  id: string;
  role: Role;
  content: string;
  timestamp: number;
}

export interface ChatPayload {
  historial: { role: string; content: string }[];
  archivos: Record<string, string>;
  asignatura: Asignatura;
  terminal_context?: string;
}

export interface ExecutePayload {
  archivos: Record<string, string>;
}

export interface ExecuteResponse {
  output: string;
  isError: boolean;
}

// Interfaz para props comunes de componentes
export interface BaseComponentProps {
  className?: string;
}