import { useRef } from 'react';
import { Download, Play, Bot, ChevronRight, ChevronLeft, Loader2, FolderOpen } from 'lucide-react';

interface TopBarProps {
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDownload: () => void;
  onRun: () => void;
  isCompiling: boolean;
  isChatOpen: boolean;
  toggleChat: () => void;
}

export default function TopBar({ onUpload, onDownload, onRun, isCompiling, isChatOpen, toggleChat }: TopBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="p-3 bg-gray-900 border-b border-gray-800 flex justify-between items-center h-[56px]">
      <div className="flex items-center gap-2">
        <input 
          type="file" 
          ref={fileInputRef}
          onChange={onUpload}
          className="hidden"
          {...{"webkitdirectory": "", "directory": ""}} 
          multiple 
        />
        <button onClick={() => fileInputRef.current?.click()} className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 transition flex items-center gap-2 border border-gray-700 shadow-sm">
          <FolderOpen size={14} className="text-blue-400" />
          Subir
        </button>
        <button onClick={onDownload} className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 transition flex items-center gap-2 border border-gray-700 shadow-sm">
          <Download size={14} className="text-emerald-400" />
          Descargar
        </button>
      </div>
      
      <div className="flex items-center gap-2">
        <button onClick={onRun} disabled={isCompiling} className={`px-4 py-1.5 rounded-md text-xs font-medium transition shadow-sm flex items-center gap-2 ${isCompiling ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}`}>
          {isCompiling ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
          {isCompiling ? 'Compilando...' : 'Ejecutar'}
        </button>
        <button onClick={toggleChat} className="px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm flex items-center gap-2 ml-2">
          {isChatOpen ? <><Bot size={14} /> Tutor <ChevronRight size={14} /></> : <><ChevronLeft size={14} /> <Bot size={14} /> Tutor</>}
        </button>
      </div>
    </div>
  );
}