import { useState } from 'react';
import { supabase } from '../../lib/supabase';
import { Cat, Globe, X } from 'lucide-react';

interface LoginProps {
  onClose?: () => void;
}

export default function Login({ onClose }: LoginProps) {
  // Estados para el email y contraseña
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleOAuthLogin = (provider: 'google' | 'github') => {
    supabase.auth.signInWithOAuth({ 
      provider, 
      options: { redirectTo: window.location.origin } 
    });
  };

  // Login con email
  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    
    if (error) {
      console.error(error.message);
    } else if (onClose) {
      onClose();
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen p-4 overflow-hidden">
      <div className="relative w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-2xl scale-90 md:scale-100">
        
        {/* Boton cerrar */}
        {onClose && (
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        )}

        <h1 className="text-2xl font-bold text-center mb-6">Acceso Tutor IA</h1>
        
        {/* Formulario de email */}
        <form onSubmit={handleEmailLogin} className="flex flex-col gap-3 mb-6">
          <input 
            type="email" 
            placeholder="Correo electrónico" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 outline-none" 
            required
          />
          <input 
            type="password" 
            placeholder="Contraseña" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 outline-none" 
            required
          />
          <button 
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 rounded-lg transition-all mt-2"
          >
            Entrar con Email
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-gray-800"></span>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-gray-900 px-2 text-gray-500">O continuar con</span>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <button 
            onClick={() => handleOAuthLogin('google')} 
            className="w-full flex items-center justify-center gap-3 bg-white text-black py-2.5 rounded-lg font-semibold hover:bg-gray-200 transition-all shadow-md active:scale-[0.98]"
          >
            <Globe size={18} /> Google
          </button>
          <button 
            onClick={() => handleOAuthLogin('github')} 
            className="w-full flex items-center justify-center gap-3 bg-gray-800 text-white py-2.5 rounded-lg font-semibold hover:bg-gray-700 transition-all shadow-md active:scale-[0.98]"
          >
            <Cat size={18} /> GitHub
          </button>
        </div>
      </div>
    </div>
  );
}