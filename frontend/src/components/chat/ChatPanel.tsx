import { useState, useRef, useEffect } from 'react';
import type { Message } from '../../types/index.ts';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  onClearChat: () => void; 
  isLoading: boolean;
}

export default function ChatPanel({ messages, onSendMessage, onClearChat, isLoading }: ChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
      {/* Header del Chat con botón de Limpiar */}
      <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
          Tutor IA
        </h2>
        <button
          onClick={onClearChat}
          disabled={isLoading || messages.length === 0}
          className="text-gray-400 hover:text-red-400 disabled:opacity-50 transition-colors text-xs flex items-center gap-1"
          title="Limpiar conversación"
        >
          {/* Icono de papelera (SVG) */}
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          Limpiar
        </button>
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
            <div className="text-sm leading-relaxed prose prose-invert max-w-none">
              <ReactMarkdown
                components={{
                  code({  inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <div className="mt-2 mb-2 rounded-md overflow-hidden border border-gray-700">
                        <SyntaxHighlighter
                          style={vscDarkPlus as any}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ margin: 0, padding: '1rem', fontSize: '0.85rem' }}
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      </div>
                    ) : (
                      <code 
                        className="bg-black/30 text-pink-300 px-1.5 py-0.5 rounded font-mono text-xs" 
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                }}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        
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