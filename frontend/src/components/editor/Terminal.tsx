import { TerminalSquare } from 'lucide-react';

interface TerminalPanelProps {
  output: string;
  isError: boolean;
}

export default function TerminalPanel({ output, isError }: TerminalPanelProps) {
  return (
    <div className="h-full bg-[#111111] border-t border-gray-800 flex flex-col">
      <div className="px-4 py-1.5 bg-[#181818] border-b border-gray-800 text-xs text-gray-400 font-mono uppercase tracking-wider flex items-center gap-2">
        <TerminalSquare size={12} />
        Consola
      </div>
      <div className={`p-4 font-mono text-sm overflow-y-auto h-full whitespace-pre-wrap ${isError ? 'text-red-400' : 'text-gray-300'}`}>
        {output}
      </div>
    </div>
  );
}