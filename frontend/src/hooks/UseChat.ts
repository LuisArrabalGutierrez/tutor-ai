import { useState, useRef } from 'react';
import type { Message, Asignatura, ChatPayload } from '../types/index.ts';
import { sendMessageStreamToBackend } from '../services/api';

export function useChat(projectFiles: Record<string, string>) {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: '¡Hola! Soy tu tutor de la UGR. ¿En qué te ayudo?', timestamp: Date.now() }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);
  
  // Guardamos el controlador actual para poder cancelarlo
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = async (text: string, asignatura: Asignatura, terminalContext: string) => {
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() };
    const assistantId = (Date.now() + 1).toString();
    
    // Inyectamos el mensaje del usuario y creamos el placeholder del asistente para streaming inmediato
    const newHistory = [...messages, userMsg];
    setMessages([...newHistory, { id: assistantId, role: 'assistant', content: '', timestamp: Date.now() }]);
    setIsAiTyping(true);

    // Creamos un nuevo controlador para esta petición
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    // Timeout de seguridad de 45 segundos
    const timeoutId = setTimeout(() => controller.abort('TIMEOUT'), 45000);

    try {
      const payload: ChatPayload = {
        historial: newHistory.map(m => ({ role: m.role, content: m.content })),
        archivos: projectFiles,
        asignatura,
        terminal_context: terminalContext
      };

      // Streaming en tiempo real token a token
      await sendMessageStreamToBackend(
        payload,
        (tokenChunk: string) => {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantId ? { ...msg, content: msg.content + tokenChunk } : msg
            )
          );
        },
        controller.signal
      );
      
    } catch (error: any) {
      const errorMsg: Message = { 
        id: 'err-' + Date.now(), 
        role: 'system', 
        content: ` ${error.message || "Conexión interrumpida."}`, 
        timestamp: Date.now() 
      };
      
      // Si el asistente no llegó a escribir nada antes del error, limpiamos el placeholder vacío
      setMessages(prev => {
        const filtered = prev.filter(m => !(m.id === assistantId && m.content.trim() === ''));
        return [...filtered, errorMsg];
      });
    } finally {
      clearTimeout(timeoutId);
      abortControllerRef.current = null;
      setIsAiTyping(false);
    }
  };

  // Función para parar la IA manualmente
  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort('MANUAL_STOP');
    }
  };

  return { 
    messages, 
    isAiTyping, 
    handleSendMessage, 
    stopGeneration,
    clearChat: () => setMessages([]) 
  };
}
