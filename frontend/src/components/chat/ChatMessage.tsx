import type { Message } from '../../types/index';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FileCode } from 'lucide-react';

interface ChatMessageProps {
  msg: Message;
}

export default function ChatMessage({ msg }: ChatMessageProps) {
  return (
    <div className={`p-4 rounded-xl max-w-[85%] shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white self-end rounded-tr-sm' : 'bg-gray-800 text-gray-200 self-start rounded-tl-sm border border-gray-700'}`}>
      <div className="text-sm leading-relaxed prose prose-invert max-w-none">
        <ReactMarkdown
          components={{
            strong({ children }) {
              const text = String(children);
              if (text.endsWith('.pdf')) {
                const baseUrl = import.meta.env.VITE_SUPABASE_URL_APUNTES;
                const pdfUrl = `${baseUrl}${encodeURIComponent(text)}`;
                return (
                  <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 px-2 py-1 mt-1 bg-red-900/40 text-red-300 rounded border border-red-800/50 hover:bg-red-800/60 transition-colors cursor-pointer no-underline text-xs font-medium">
                    <FileCode size={12} /> {text}
                  </a>
                );
              }
              return <strong className="font-semibold text-white">{children}</strong>;
            },
            code({ inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <div className="mt-3 mb-3 rounded-lg overflow-hidden border border-gray-700 shadow-inner">
                  <SyntaxHighlighter style={vscDarkPlus as any} language={match[1]} PreTag="div" customStyle={{ margin: 0, padding: '1rem', fontSize: '0.85rem', background: '#111111' }} {...props}>
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <code className="bg-black/40 text-blue-300 px-1.5 py-0.5 rounded font-mono text-[0.8em] border border-gray-700/50" {...props}>
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
  );
}