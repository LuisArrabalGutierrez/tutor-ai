import { supabase } from '../lib/supabase';
import type { ChatPayload, ExecuteResponse } from '../types/index.ts';

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

const API_URL = isLocal ? (import.meta.env.VITE_API_URL || 'http://localhost:8000') : '';

// Tiempos de espera configurables
//const CHAT_TIMEOUT = 45000;
const EXECUTE_TIMEOUT = 15000;

// Envía el mensaje al backend con el token de usuario y maneja la cancelación.
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