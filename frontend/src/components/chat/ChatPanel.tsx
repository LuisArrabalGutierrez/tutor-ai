import { useRef, useEffect } from 'react';
import type { Message } from '../../types/index.ts';
import { Trash2, BotMessageSquare } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  onClearChat: () => void; 
  isLoading: boolean;
}

export default function ChatPanel({ messages, onSendMessage, onClearChat, isLoading }: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full w-full bg-gray-950">
      <div className="p-3 bg-gray-900 border-b border-gray-800 flex justify-between items-center h-[56px]">
        <h2 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
          <BotMessageSquare size={18} /> Tutor IA
        </h2>
        <button onClick={onClearChat} disabled={isLoading || messages.length === 0} className="text-gray-400 hover:text-red-400 disabled:opacity-50 transition-colors text-xs flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-800">
          <Trash2 size={14} /> Limpiar
        </button>
      </div>
      
      <div className="flex-grow p-4 overflow-y-auto flex flex-col gap-4">
        {messages.map((msg) => <ChatMessage key={msg.id} msg={msg} />)}
        {isLoading && (
          <div className="bg-gray-800 p-4 rounded-xl self-start rounded-tl-sm border border-gray-700 flex gap-2 items-center shadow-sm">
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
}