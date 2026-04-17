const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const sendMessageToBackend = async (
  messages: {role: string, content: string}[], 
  projectFiles: Record<string, string>,
  asignatura: 'cpp' | 'linux' = 'cpp', // Nuevo parámetro
  terminalContext: string = ''         // Nuevo parámetro
): Promise<string> => {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // Hacemos que coincida EXACTAMENTE con el BaseModel de FastAPI
      body: JSON.stringify({ 
        historial: messages,       // Cambiado de 'mensajes' a 'historial'
        archivos: projectFiles, 
        asignatura: asignatura,
        terminal_context: terminalContext
      }), 
    });

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status}`);
    }

    const data = await response.json();
    // Aceptamos data.reply (como lo configuramos hoy) o data.respuesta (tu formato antiguo) por seguridad
    return data.reply || data.respuesta; 
    
  } catch (error) {
    console.error("Error conectando con el backend:", error);
    throw new Error("No se pudo conectar con la IA. ¿Está encendido el servidor Python?");
  }
};

export const executeCodeBackend = async (
  projectFiles: Record<string, string>
): Promise<{output: string, isError: boolean}> => {
    const endpoint = `${API_URL}/api/execute`;
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archivos: projectFiles }), 
      });
  
      if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
  
      const data = await response.json();
      return data;
      
    } catch (error) {
      console.error("Error al ejecutar código:", error);
      return { 
        output: "❌ Error de red: No se pudo conectar con el servidor para compilar. ¿Está el backend encendido?", 
        isError: true 
      };
    }
};