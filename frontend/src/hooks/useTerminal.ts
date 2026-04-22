import { useState } from 'react';
import { executeCodeBackend } from '../services/api';

{/* Hook personalizado para manejar la lógica del terminal,
   incluyendo el estado de la salida del terminal, el estado de compilación, 
   el estado de error del terminal, la función para ejecutar el código en el backend,
    y la función para establecer un mensaje personalizado en el terminal */ }
export function useTerminal(projectFiles: Record<string, string>) {
  const [terminalOutput, setTerminalOutput] = useState<string>("Sube una carpeta o presiona 'Ejecutar'...");
  const [isCompiling, setIsCompiling] = useState(false);
  const [isTerminalError, setIsTerminalError] = useState(false);

  {/* Función para manejar la ejecución del código en el backend, que establece el estado de compilación y el mensaje del terminal,
   luego llama a la función executeCodeBackend para enviar los archivos del proyecto al backend y obtener la salida del terminal,
    y finalmente actualiza el estado del terminal con la salida obtenida y el estado de error, y establece el estado de compilación a false */ }
  const handleRunCode = async () => {
    setIsCompiling(true);
    setTerminalOutput("Compilando...");
    setIsTerminalError(false);
    
    const result = await executeCodeBackend(projectFiles);
    
    setTerminalOutput(result.output);
    setIsTerminalError(result.isError);
    setIsCompiling(false);
  };

  const setTerminalMessage = (msg: string, isError: boolean = false) => {
    setTerminalOutput(msg);
    setIsTerminalError(isError);
  };

  return { terminalOutput, isCompiling, isTerminalError, handleRunCode, setTerminalMessage };
}