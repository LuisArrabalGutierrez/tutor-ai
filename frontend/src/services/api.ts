const API_URL = import.meta.env.VITE_API_URL

export const sendMessageToBackend = async (
  messages: {role: string, content: string}[], 
  projectFiles: Record<string, string> 
): Promise<string> => {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        mensajes: messages, 
        archivos: projectFiles 
      }), 
    });

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status}`);
    }

    const data = await response.json();
    return data.respuesta; 
    
  } catch (error) {
    console.error("Error conectando con el backend:", error);
    throw new Error("No se pudo conectar con la IA. ¿Está encendido el servidor Python?");
  }
};

export const executeCodeBackend = async (projectFiles: Record<string, string>): Promise<{output: string, isError: boolean}> => {
    const API_URL = import.meta.env.VITE_API_URL;
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