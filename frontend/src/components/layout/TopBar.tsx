import { useRef } from 'react';
import { Download, Play, Loader2, FolderOpen, Code2, TerminalSquare, Bot } from 'lucide-react';
import type { Asignatura } from '../../types';

interface TopBarProps {
  asignaturaActual: Asignatura;
  onCambiarAsignatura: (a: Asignatura) => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDownload: () => void;
  onRun: () => void;
  isCompiling: boolean;
  isChatOpen: boolean;
  toggleChat: () => void;
}

export default function TopBar({ 
  asignaturaActual, onCambiarAsignatura, onUpload, onDownload, onRun, isCompiling, isChatOpen, toggleChat 
}: TopBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <header className="p-3 bg-gray-900 border-b border-gray-800 flex justify-between items-center h-[56px] shrink-0">
      <div className="flex items-center gap-4">
        {/* Selector de Asignatura */}
        <div className="flex items-center bg-gray-800 rounded-md p-1 border border-gray-700 shadow-sm">
          <button 
            onClick={() => onCambiarAsignatura('cpp')}
            className={`flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-sm transition-all ${asignaturaActual === 'cpp' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <Code2 size={14} /> C/C++
          </button>
          <button 
            onClick={() => onCambiarAsignatura('linux')}
            className={`flex items-center gap-2 px-3 py-1 text-xs font-medium rounded-sm transition-all ${asignaturaActual === 'linux' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <TerminalSquare size={14} /> Linux
          </button>
        </div>

        {/* Acciones de Archivo */}
        {asignaturaActual === 'cpp' && (
          <div className="flex items-center gap-2 border-l border-gray-700 pl-4">
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={onUpload} 
              className="hidden" 
              // @ts-ignore - Atributos no estándar para subir carpetas
              webkitdirectory="" 
              directory="" 
            />
            <button onClick={() => fileInputRef.current?.click()} className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 transition flex items-center gap-2 border border-gray-700">
              <FolderOpen size={14} className="text-blue-400" /> Subir Carpeta
            </button>
            <button onClick={onDownload} className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 transition flex items-center gap-2 border border-gray-700">
              <Download size={14} className="text-emerald-400" /> Descargar ZIP
            </button>
          </div>
        )}
      </div>
      
      <div className="flex items-center gap-2">
        {asignaturaActual === 'cpp' && (
          <button 
            onClick={onRun} 
            disabled={isCompiling} 
            className={`px-4 py-1.5 rounded-md text-xs font-medium transition shadow-sm flex items-center gap-2 ${isCompiling ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}`}
          >
            {isCompiling ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}
            Ejecutar
          </button>
        )}

        <button 
          onClick={toggleChat} 
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-2 border ${isChatOpen ? 'bg-blue-600 text-white border-blue-500' : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'}`}
        >
          <div className="relative">
             <Bot size={16} /> 
             {isChatOpen && <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full border border-gray-900 animate-pulse" />}
          </div>
          Tutor IA
        </button>
      </div>
    </header>
  );
}