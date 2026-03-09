import { useState, useRef, useEffect } from 'react';
import type { Message } from '../../types/index.ts';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
}

export default function ChatPanel({ messages, onSendMessage, isLoading }: ChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll hacia abajo cuando hay un nuevo mensaje
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-950 w-full">
      {/* Header del Chat */}
      <div className="p-4 bg-gray-800 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
          Tutor IA
        </h2>
      </div>
      
      {/* Historial de Mensajes */}
      <div className="flex-grow p-4 overflow-y-auto flex flex-col gap-4">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`p-3 rounded-lg max-w-[85%] ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white self-end rounded-tr-none' 
                : 'bg-gray-800 text-gray-200 self-start rounded-tl-none border border-gray-700'
            }`}
          >
            <p className="text-sm leading-relaxed">{msg.content}</p>
          </div>
        ))}
        
        {/* Indicador de "Escribiendo..." */}
        {isLoading && (
          <div className="bg-gray-800 p-3 rounded-lg self-start rounded-tl-none border border-gray-700 flex gap-1 items-center">
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input de Texto */}
      <form onSubmit={handleSubmit} className="p-4 bg-gray-900 border-t border-gray-700 flex gap-2">
        <input 
          type="text" 
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ej: ¿Por qué falla mi bucle for?" 
          disabled={isLoading}
          className="flex-grow bg-gray-800 text-white rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 transition-colors"
        />
        <button 
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded-md text-sm transition font-medium"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}