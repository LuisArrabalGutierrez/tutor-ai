import { useRef } from 'react';
import { Download, Play, Bot, ChevronRight, ChevronLeft, Loader2, FolderOpen, Code2, TerminalSquare } from 'lucide-react';

interface TopBarProps {
  asignaturaActual: 'cpp' | 'linux';
  onCambiarAsignatura: (asignatura: 'cpp' | 'linux') => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDownload: () => void;
  onRun: () => void;
  isCompiling: boolean;
  isChatOpen: boolean;
  toggleChat: () => void;
}

export default function TopBar({ 
  asignaturaActual, onCambiarAsignatura, onUpload, onDownload, onRun, isCompiling, isChatOpen, toggleChat }: TopBarProps) {
  
    const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="p-3 bg-gray-900 border-b border-gray-800 flex justify-between items-center h-[56px]">
      <div className="flex items-center gap-4">
        {/* Selector de Asignatura */}
        <div className="relative flex items-center bg-gray-800 rounded-md p-1 border border-gray-700 shadow-sm">
          <button 
            onClick={() => onCambiarAsignatura('cpp')}
            className={`flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-sm transition-colors ${asignaturaActual === 'cpp' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <Code2 size={14} />
            C/C++
          </button>
          <button 
            onClick={() => onCambiarAsignatura('linux')}
            className={`flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-sm transition-colors ${asignaturaActual === 'linux' ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <TerminalSquare size={14} />
            Linux
          </button>
        </div>

        {/* Botones de gestión de archivos (Solo en C++) */}
        {asignaturaActual === 'cpp' && (
          <div className="flex items-center gap-2 ml-2 border-l border-gray-700 pl-4">
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
        )}
      </div>
      
      <div className="flex items-center gap-2">
        {/* Botón de Ejecutar (Solo en C++) */}
        {asignaturaActual === 'cpp' && (
          <button onClick={onRun} disabled={isCompiling} className={`px-4 py-1.5 rounded-md text-xs font-medium transition shadow-sm flex items-center gap-2 ${isCompiling ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}`}>
            {isCompiling ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
            {isCompiling ? 'Compilando...' : 'Ejecutar'}
          </button>
        )}

        {/* Botón del Tutor IA (Siempre visible) */}
        <button onClick={toggleChat} className="px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm flex items-center gap-2 ml-2">
          {isChatOpen ? <><Bot size={14} /> Tutor <ChevronRight size={14} /></> : <><ChevronLeft size={14} /> <Bot size={14} /> Tutor</>}
        </button>
      </div>
    </div>
  );
}