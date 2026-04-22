import { useState } from 'react';
import type { Message, Asignatura, ChatPayload } from '../types/index.ts';
import { sendMessageToBackend } from '../services/api';

{/* Hook personalizado para manejar la lógica del chat, incluyendo el historial de mensajes,
   el estado de "escribiendo" de la IA, y la función para enviar mensajes al backend */ }

export function useChat(projectFiles: Record<string, string>) {

  {/* Estado para almacenar el historial de mensajes del chat, que se inicializa con un mensaje de bienvenida de la ia */ }
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: '¡Hola! Soy tu tutor de la UGR. ¿En qué te ayudo?', timestamp: Date.now() }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);

  {/* Función para manejar el envío de un mensaje por parte del usuario, que actualiza el historial de mensajes,
     establece el estado de "escribiendo" de la IA, y luego envía el mensaje al backend para obtener la respuesta del asistente */ }
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

  {/* La función clearChat se ha integrado directamente en el return para simplificar su uso,
     y permite limpiar el historial de mensajes del chat estableciendo el estado de messages a un array vacío 
     que se usa cuando le da al boton de l ui de bprrar historial*/ }
  return { messages, isAiTyping, handleSendMessage, clearChat: () => setMessages([]) };
}