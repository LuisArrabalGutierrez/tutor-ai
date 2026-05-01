import { useState, useRef } from 'react';
import type { Message, Asignatura, ChatPayload } from '../types/index.ts';
import { sendMessageToBackend } from '../services/api';

export function useChat(projectFiles: Record<string, string>) {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: '¡Hola! Soy tu tutor de la UGR. ¿En qué te ayudo?', timestamp: Date.now() }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);
  
  // Guardamos el controlador actual para poder cancelarlo
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = async (text: string, asignatura: Asignatura, terminalContext: string) => {
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() };
    const newHistory = [...messages, userMsg];
    
    setMessages(newHistory);
    setIsAiTyping(true);

    // Creamos un nuevo controlador para esta petición
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    // Mantenemos tu timeout de seguridad de 45 segundos
    const timeoutId = setTimeout(() => controller.abort('TIMEOUT'), 45000);

    try {
      const payload: ChatPayload = {
        historial: newHistory.map(m => ({ role: m.role, content: m.content })),
        archivos: projectFiles,
        asignatura,
        terminal_context: terminalContext
      };

      // Le pasamos la señal de aborto a la API
      const reply = await sendMessageToBackend(payload, controller.signal);
      
      const assistantMsg: Message = { id: Date.now().toString(), role: 'assistant', content: reply, timestamp: Date.now() };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error: any) {
      const errorMsg: Message = { 
        id: 'err-' + Date.now(), 
        role: 'system', 
        content: ` ${error.message || "Conexión interrumpida."}`, 
        timestamp: Date.now() 
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      clearTimeout(timeoutId);
      abortControllerRef.current = null;
      setIsAiTyping(false);
    }
  };

  // Función para parar la IA manualmente
  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort('MANUAL_STOP'); // Cancelamos la petición
    }
  };

  return { 
    messages, 
    isAiTyping, 
    handleSendMessage, 
    stopGeneration, // Exportamos la nueva función
    clearChat: () => setMessages([]) 
  };
}