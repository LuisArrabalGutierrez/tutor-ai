import { useState } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-gray-900 border-t border-gray-800 flex gap-2">
      <input 
        type="text" 
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Pregúntale algo a tu tutor..." 
        disabled={isLoading}
        className="flex-grow bg-gray-950 border border-gray-700 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 transition-all placeholder-gray-500"
      />
      <button 
        type="submit"
        disabled={isLoading || !inputValue.trim()}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 disabled:border-gray-700 text-white px-4 py-2.5 rounded-lg transition-all flex items-center justify-center border border-transparent shadow-sm"
      >
        <Send size={16} className={!inputValue.trim() ? "opacity-50" : ""} />
      </button>
    </form>
  );
}