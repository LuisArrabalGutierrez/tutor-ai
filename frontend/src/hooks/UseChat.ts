import { useState } from 'react';
import type { Message, Asignatura, ChatPayload } from '../types/index.ts';
import { sendMessageToBackend } from '../services/api';

export function useChat(projectFiles: Record<string, string>) {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: '¡Hola! Soy tu tutor de la UGR. ¿En qué te ayudo?', timestamp: Date.now() }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);

  const handleSendMessage = async (text: string, asignatura: Asignatura, terminalContext: string) => {
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() };
    const newHistory = [...messages, userMsg];
    
    setMessages(newHistory);
    setIsAiTyping(true);

    try {
      const payload: ChatPayload = {
        historial: newHistory.map(m => ({ role: m.role, content: m.content })),
        archivos: projectFiles,
        asignatura,
        terminal_context: terminalContext
      };

      const reply = await sendMessageToBackend(payload);
      
      const assistantMsg: Message = { id: Date.now().toString(), role: 'assistant', content: reply, timestamp: Date.now() };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error: any) {
      const errorMsg: Message = { 
        id: 'err-' + Date.now(), 
        role: 'system', 
        content: `❌ ${error.message || "Error de conexión."}`, 
        timestamp: Date.now() 
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsAiTyping(false);
    }
  };

  return { messages, isAiTyping, handleSendMessage, clearChat: () => setMessages([]) };
}