import { useState } from 'react';
import { executeCodeBackend } from '../services/api';

export function useTerminal(projectFiles: Record<string, string>) {
  const [terminalOutput, setTerminalOutput] = useState<string>("Sube una carpeta o presiona 'Ejecutar'...");
  const [isCompiling, setIsCompiling] = useState(false);
  const [isTerminalError, setIsTerminalError] = useState(false);

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