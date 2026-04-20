import { useRef, useEffect, memo } from 'react';
import { Trash2, BotMessageSquare } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import {type  Message } from '../../types';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  onClearChat: () => void; 
  isLoading: boolean;
}

// Usamos memo para evitar re-renders innecesarios del panel si las props no cambian
export default memo(function ChatPanel({ messages, onSendMessage, onClearChat, isLoading }: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full w-full bg-gray-950 border-l border-gray-800">
      {/* Header del Chat */}
      <div className="p-3 bg-gray-900 border-b border-gray-800 flex justify-between items-center h-[56px] shrink-0">
        <h2 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
          <BotMessageSquare size={18} /> Tutor IA Socrático
        </h2>
        <button 
          onClick={onClearChat} 
          disabled={isLoading || messages.length <= 1} 
          className="text-gray-400 hover:text-red-400 disabled:opacity-30 transition-all text-xs flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-800"
        >
          <Trash2 size={14} /> Borrar historial
        </button>
      </div>
      
      {/* Área de Mensajes */}
      <div className="flex-grow p-4 overflow-y-auto flex flex-col gap-4 scrollbar-thin scrollbar-thumb-gray-800">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}
        
        {isLoading && (
          <div className="bg-gray-800/50 p-4 rounded-xl self-start rounded-tl-sm border border-gray-700 flex gap-2 items-center shadow-sm">
            <span className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
              <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
              <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"></span>
            </span>
            <span className="text-xs text-gray-400 font-medium ml-1">Escribiendo...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <ChatInput onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
});