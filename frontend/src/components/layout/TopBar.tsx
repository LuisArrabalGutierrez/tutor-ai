import { useRef } from 'react';
import { Download, Play, Loader2, FolderOpen, Code2, TerminalSquare, Bot, User, LogOut, LogIn } from 'lucide-react';
import type { Asignatura } from '../../types';
import { supabase } from '../../lib/supabase'; // Asegúrate de que esta ruta sea correcta según tu estructura

interface TopBarProps {
  asignaturaActual: Asignatura;
  onCambiarAsignatura: (a: Asignatura) => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDownload: () => void;
  onRun: () => void;
  isCompiling: boolean;
  isChatOpen: boolean;
  toggleChat: () => void;
  userEmail?: string | null; // Nuevo
  onOpenLogin: () => void;   // Nuevo
}

export default function TopBar({ 
  asignaturaActual, onCambiarAsignatura, onUpload, onDownload, onRun, isCompiling, isChatOpen, toggleChat, userEmail, onOpenLogin
}: TopBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Función para cerrar sesión
  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.reload(); // Recarga la app para limpiar el estado
  };

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
        {/* Ejecutar */}
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

        {/* Chat */}
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

        {/* Separador Visual */}
        <div className="w-px h-6 bg-gray-700 mx-2"></div>

        {/* Sistema de Usuario */}
        {userEmail ? (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-full group relative cursor-pointer">
            <User size={14} className="text-blue-400" />
            <span className="text-[11px] font-medium text-gray-300 max-w-[120px] truncate">
              {userEmail}
            </span>
            
            {/* Menú desplegable */}
            <div className="absolute top-full right-0 mt-2 w-40 bg-gray-900 border border-gray-800 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-all z-50">
              <button 
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-xs text-red-400 hover:bg-red-950/20 rounded-lg transition-colors"
              >
                <LogOut size={14} /> Cerrar Sesión
              </button>
            </div>
          </div>
        ) : (
          <button 
            onClick={onOpenLogin}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-md text-xs font-medium transition-all shadow-sm"
          >
            <LogIn size={14} /> Entrar
          </button>
        )}
      </div>
    </header>
  );
}