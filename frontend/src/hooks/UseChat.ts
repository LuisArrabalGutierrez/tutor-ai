import { useState } from 'react';
import type { Message } from '../types/index';
import { sendMessageToBackend } from '../services/api';

export function useChat(projectFiles: Record<string, string>) {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: '¡Hola! Soy tu tutor de la UGR. ¿En qué te ayudo?', timestamp: Date.now() }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);

  // 1. Añadimos 'asignatura' y 'terminalContext' como parámetros
  const handleSendMessage = async (text: string, asignatura: 'cpp' | 'linux' = 'cpp', terminalContext: string = '') => {
    const chat = [...messages, { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() } as Message];
    setMessages(chat);
    setIsAiTyping(true);
    
    try {
      // 2. Pasamos esos nuevos datos a la función de la API
      const reply = await sendMessageToBackend(
        chat.map(m => ({ role: m.role, content: m.content })), 
        projectFiles,
        asignatura,
        terminalContext
      );
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: reply, timestamp: Date.now() }]);
    } catch {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'system', content: '❌ Error de conexión con el Tutor IA.', timestamp: Date.now() }]);
    } finally {
      setIsAiTyping(false);
    }
  };

  const clearChat = () => setMessages([]);

  return { messages, isAiTyping, handleSendMessage, clearChat };
}