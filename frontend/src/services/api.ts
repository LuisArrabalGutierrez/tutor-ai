const API_URL = import.meta.env.VITE_API_URL

export const sendMessageToBackend = async (message: string, code: string): Promise<string> => {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // TRADUCCIÓN: Convertimos las variables de React a las que espera FastAPI
      body: JSON.stringify({ 
        pregunta: message, 
        codigo: code 
      }), 
    });

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status}`);
    }

    const data = await response.json();
    // TRADUCCIÓN: Leemos "respuesta" que es lo que devuelve el backend en Python
    return data.respuesta; 
    
  } catch (error) {
    console.error("Error conectando con el backend:", error);
    throw new Error("No se pudo conectar con la IA. ¿Está encendido el servidor Python?");
  }
};

export const executeCodeBackend = async (code: string): Promise<{output: string, isError: boolean}> => {
    const API_URL = import.meta.env.VITE_API_URL;
    const endpoint = `${API_URL}/api/execute`;
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }), 
      });
  
      if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
  
      // El backend nos devuelve exactamente {"output": "...", "isError": true/false}
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