import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Autofocus al cargar y cuando deja de cargar la IA
  useEffect(() => {
    if (!isLoading) inputRef.current?.focus();
  }, [isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedValue = inputValue.trim();
    if (trimmedValue && !isLoading) {
      onSendMessage(trimmedValue);
      setInputValue('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-gray-900 border-t border-gray-800 flex gap-2 items-center">
      <input 
        ref={inputRef}
        type="text" 
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={isLoading ? "El tutor está pensando..." : "Pregúntale algo a tu tutor..."} 
        disabled={isLoading}
        className="flex-grow bg-gray-950 border border-gray-700 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 transition-all placeholder-gray-600"
      />
      <button 
        type="submit"
        disabled={isLoading || !inputValue.trim()}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 disabled:border-gray-700 text-white p-2.5 rounded-lg transition-all shadow-lg active:scale-95 flex items-center justify-center shrink-0"
        title="Enviar mensaje"
      >
        <Send size={18} className={isLoading ? "opacity-0" : "opacity-100"} />
      </button>
    </form>
  );
}