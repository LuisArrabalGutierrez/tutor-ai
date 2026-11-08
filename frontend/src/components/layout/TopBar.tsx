import { useRef } from 'react';
import { Download, Play, Loader2, FolderOpen, Code2, TerminalSquare, Bot, User, LogOut, LogIn } from 'lucide-react';
import type { Asignatura } from '../../types';
import { supabase } from '../../lib/supabase';

interface TopBarProps {
  asignaturaActual: Asignatura;
  onCambiarAsignatura: (a: Asignatura) => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDownload: () => void;
  onRun: () => void;
  isCompiling: boolean;
  isChatOpen: boolean;
  toggleChat: () => void;
  userEmail?: string | null;
  onOpenLogin: () => void;
}

export default function TopBar({ 
  asignaturaActual, onCambiarAsignatura, onUpload, onDownload, onRun, isCompiling, isChatOpen, toggleChat, userEmail, onOpenLogin
}: TopBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.reload();
  };

  return (
    <header className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex justify-between items-center h-[52px] w-full shrink-0 z-20 shadow-md">
      {/* Sección Izquierda: Identidad + Selector de Asignatura + Acciones */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Branding UGR */}
        <div className="flex items-center gap-2 shrink-0 select-none mr-1">
          <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 shadow-sm">
            <Bot size={16} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-sm tracking-tight text-white hidden sm:inline">Tutor IA</span>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700/50 uppercase tracking-wider">
              UGR
            </span>
          </div>
        </div>

        <div className="w-px h-5 bg-gray-800 hidden sm:block shrink-0" />

        {/* Selector de Asignatura */}
        <div className="flex items-center bg-gray-800/90 rounded-md p-0.5 border border-gray-700/80 shadow-sm shrink-0">
          <button 
            onClick={() => onCambiarAsignatura('cpp')}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded transition-all ${asignaturaActual === 'cpp' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <Code2 size={13} /> C/C++
          </button>
          <button 
            onClick={() => onCambiarAsignatura('linux')}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded transition-all ${asignaturaActual === 'linux' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <TerminalSquare size={13} /> Linux
          </button>
        </div>

        {/* Acciones de Archivo y Ejecución (Modo C++) */}
        {asignaturaActual === 'cpp' && (
          <div className="flex items-center gap-2 border-l border-gray-800 pl-3">
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={onUpload} 
              className="hidden" 
              // @ts-expect-error webkitdirectory no está en los tipos de React
              webkitdirectory="" 
              directory="" 
            />
            <button 
              onClick={() => fileInputRef.current?.click()} 
              className="px-2.5 py-1 rounded-md text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-200 transition flex items-center gap-1.5 border border-gray-700 shadow-sm"
              title="Cargar carpeta de proyecto C++"
            >
              <FolderOpen size={13} className="text-blue-400" /> Subir Carpeta
            </button>
            <button 
              onClick={onDownload} 
              className="px-2.5 py-1 rounded-md text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-200 transition flex items-center gap-1.5 border border-gray-700 shadow-sm"
              title="Descargar proyecto en archivo ZIP"
            >
              <Download size={13} className="text-emerald-400" /> Descargar ZIP
            </button>
            <button 
              onClick={onRun} 
              disabled={isCompiling} 
              className={`px-3 py-1 rounded-md text-xs font-semibold transition shadow-sm flex items-center gap-1.5 ${isCompiling ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700' : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950'}`}
              title="Compilar y ejecutar en sandbox seguro"
            >
              {isCompiling ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} fill="currentColor" />}
              Ejecutar
            </button>
          </div>
        )}
      </div>
      
      {/* Sección Derecha: Botón Tutor IA + Usuario */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Toggle Tutor IA */}
        <button 
          onClick={toggleChat} 
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-2 border shadow-sm ${isChatOpen ? 'bg-blue-600 text-white border-blue-500 shadow-blue-950' : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700 hover:text-white'}`}
          title={isChatOpen ? "Ocultar panel del Tutor IA" : "Mostrar panel del Tutor IA"}
        >
          <div className="relative">
             <Bot size={15} /> 
             {isChatOpen && <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full border border-gray-900 animate-pulse" />}
          </div>
          <span>Tutor IA</span>
        </button>

        <div className="w-px h-5 bg-gray-800 shrink-0" />

        {/* Sistema de Usuario */}
        {userEmail ? (
          <div className="flex items-center gap-2 px-3 py-1 bg-gray-800/90 hover:bg-gray-800 border border-gray-700 rounded-full group relative cursor-pointer transition">
            <User size={13} className="text-blue-400" />
            <span className="text-[11px] font-medium text-gray-300 max-w-[160px] truncate" title={userEmail}>
              {userEmail}
            </span>
            
            {/* Menú desplegable */}
            <div className="absolute top-full right-0 mt-2 w-44 bg-gray-900 border border-gray-800 rounded-lg shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-all z-50 p-1">
              <button 
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-950/30 rounded-md transition-colors"
              >
                <LogOut size={13} /> Cerrar Sesión
              </button>
            </div>
          </div>
        ) : (
          <button 
            onClick={onOpenLogin}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white border border-blue-500/80 rounded-md text-xs font-medium transition-all shadow-sm"
          >
            <LogIn size={13} /> Iniciar Sesión
          </button>
        )}
      </div>
    </header>
  );
}
