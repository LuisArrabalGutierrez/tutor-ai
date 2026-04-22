import type { ChatPayload, ExecuteResponse } from '../types/index.ts';

const API_URL = import.meta.env.VITE_API_URL || '';

// Tiempos de espera configurables
const CHAT_TIMEOUT = 45000; // 45 segundos para la IA
const EXECUTE_TIMEOUT = 15000; // 15 segundos para compilar

{/* Función para enviar un mensaje al backend y obtener la respuesta del asistente,
que incluye manejo de tiempo de espera para evitar que la IA se quede "colgada" y deje al usuario esperando indefinidamente,
y devuelve un string en un futuro async*/ }
export const sendMessageToBackend = async (payload: ChatPayload): Promise<string> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT);// Si la IA tarda más de 45 segundos en responder, se aborta la solicitud y se muestra un mensaje de error al usuario

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

{/* Función para enviar los archivos del proyecto al backend y obtener la salida del terminal, 
que también incluye manejo de tiempo de espera para evitar que el proceso de compilación se quede "colgado" y deje al usuario esperando indefinidamente 
y devuelve una respuesta en un futuro async*/ }
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