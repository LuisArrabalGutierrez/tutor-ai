import { supabase } from '../lib/supabase';
import type { ChatPayload, ExecuteResponse } from '../types/index.ts';

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

const API_URL = isLocal ? (import.meta.env.VITE_API_URL || 'http://localhost:8000') : '';
const EXECUTE_TIMEOUT = 15000;

// Envía el mensaje con Streaming (SSE) para renderizado token a token en tiempo real
export const sendMessageStreamToBackend = async (
  payload: ChatPayload,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<string> => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal
    });

    if (!response.ok) {
      // Si el stream falla, fallback transparente al endpoint síncrono
      return await sendMessageToBackend(payload, signal);
    }

    if (!response.body) {
      throw new Error("Respuesta sin cuerpo para streaming.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let fullText = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          const dataStr = trimmed.replace("data: ", "").trim();
          if (dataStr === "[DONE]") {
            break;
          }
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.token) {
              fullText += parsed.token;
              onChunk(parsed.token);
            } else if (parsed.error) {
              throw new Error(parsed.error);
            }
          } catch (e: any) {
            if (e.message && !dataStr.startsWith("{")) {
              // Si no es json o es un error lanzado
              throw e;
            }
          }
        }
      }
    }

    return fullText;

  } catch (error: any) {
    if (error.name === 'AbortError') {
      if (signal?.reason === 'MANUAL_STOP') {
        throw new Error("Generación detenida.");
      }
      throw new Error("La IA tardó demasiado en responder.");
    }
    throw error;
  }
};

// Envía el mensaje al backend con el token de usuario y maneja la cancelación (Modo Síncrono Fallback)
export const sendMessageToBackend = async (payload: ChatPayload, signal?: AbortSignal): Promise<string> => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal
    });

    if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);

    const resData = await response.json();
    return resData.reply || resData.respuesta;
    
  } catch (error: any) {
    if (error.name === 'AbortError') {
      if (signal?.reason === 'MANUAL_STOP') {
        throw new Error("Generación detenida.");
      }
      throw new Error("La IA tardó demasiado en responder.");
    }
    throw error;
  }
};

// Envía los archivos para compilar y aborta si supera el timeout.
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
