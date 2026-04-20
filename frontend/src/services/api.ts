import type { ChatPayload, ExecuteResponse } from '../types/index.ts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Tiempos de espera configurables
const CHAT_TIMEOUT = 45000; // 45 segundos para la IA
const EXECUTE_TIMEOUT = 15000; // 15 segundos para compilar

export const sendMessageToBackend = async (payload: ChatPayload): Promise<string> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT);

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);

    const data = await response.json();
    return data.reply || data.respuesta;
    
  } catch (error: any) {
    if (error.name === 'AbortError') throw new Error("La IA tardó demasiado en responder.");
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
};

export const executeCodeBackend = async (archivos: Record<string, string>): Promise<ExecuteResponse> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), EXECUTE_TIMEOUT);

  try {
    const response = await fetch(`${API_URL}/api/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ archivos }),
      signal: controller.signal
    });

    if (!response.ok) throw new Error("Error en la compilación remota.");
    return await response.json();
    
  } catch (error: any) {
    return { 
      output: error.name === 'AbortError' ? "❌ Tiempo de espera agotado (Timeout)." : "❌ Error de conexión con el compilador.", 
      isError: true 
    };
  } finally {
    clearTimeout(timeoutId);
  }
};