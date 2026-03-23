import { useState } from 'react';
import CodeEditor from './components/editor/CodeEditor';
import ChatPanel from './components/chat/ChatPanel';
import type { Message } from './types/index';
import { sendMessageToBackend, executeCodeBackend } from './services/api';

export default function App() {
  // Estados del Editor y chat
  const [code, setCode] = useState<string>(
    '#include <iostream>\n\nint main() {\n    std::cout << "¡Hola Mundo desde mi propio IDE!" << std::endl;\n    return 0;\n}'
  );

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '¡Hola! Soy tu tutor socrático. Veo que estás trabajando en `main.cpp`. ¿En qué te puedo ayudar a pensar hoy?',
      timestamp: Date.now(),
    }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);

  // nuevos Estados de la terminal
  const [terminalOutput, setTerminalOutput] = useState<string>("Presiona 'Ejecutar Código' para ver el resultado aquí...");
  const [isCompiling, setIsCompiling] = useState(false);
  const [isTerminalError, setIsTerminalError] = useState(false);

  // Función para enviar mensajes a la IA
  const handleSendMessage = async (text: string) => {
    const newUserMsg: Message = { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() };
    
    // Lista actualizada con el nuevo mensaje del usuario
    const chatActualizado = [...messages, newUserMsg];
    
    setMessages(chatActualizado);
    setIsAiTyping(true);

    try {
      // Limpiamos la lista para enviar solo rol y contenido al backend
      const historialLimpio = chatActualizado
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .map(m => ({ role: m.role, content: m.content }));

      const reply = await sendMessageToBackend(historialLimpio, code);
      
      const newAiMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: reply, timestamp: Date.now() };
      setMessages((prev) => [...prev, newAiMsg]);
    } catch (error) {
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'system', content: '❌ Error: No se pudo conectar con el servidor.', timestamp: Date.now() }]);
    } finally {
      setIsAiTyping(false);
    }
  };
  
  // Función para el botón verde (Compilar)
  const handleRunCode = async () => {
    setIsCompiling(true);
    setTerminalOutput("Compilando y ejecutando...");
    setIsTerminalError(false);

    // Llamamos a nuestro nuevo servicio
    const result = await executeCodeBackend(code);
    
    setTerminalOutput(result.output);
    setIsTerminalError(result.isError);
    setIsCompiling(false);
  };

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-white font-sans overflow-hidden">
      
      {/* MITAD IZQUIERDA: Editor + Terminal */}
      <div className="w-1/2 h-full flex flex-col border-r border-gray-700">
        
        {/* Cabecera Superior */}
        <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center h-[60px]">
          <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
            👨‍💻 <span className="font-mono text-xs">main.cpp</span>
          </h2>
          
          {/* El boton de compilar */}
          <button 
            onClick={handleRunCode}
            disabled={isCompiling}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition shadow-sm ${
              isCompiling 
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                : 'bg-green-600 hover:bg-green-500 text-white'
            }`}
          >
            {isCompiling ? 'Compilando...' : '▶ Ejecutar Código'}
          </button>
        </div>
        
        {/* editor  h-[70%] para que ocupe un 70% de la altura de la pantalla*/}
        <div className="flex-grow h-[70%]">
          <CodeEditor 
            code={code} 
            onChange={(value) => setCode(value || '')} 
            language="cpp"
          />
        </div>

        {/* terminal  h-[30%] para que ocupe un 30% de la altura de la pantalla */}
        <div className="h-[30%] bg-black border-t border-gray-700 flex flex-col">
          <div className="px-4 py-1 bg-gray-800 border-b border-gray-700 text-xs text-gray-400 font-mono uppercase tracking-wider flex justify-between">
            <span>Terminal</span>
            {isCompiling && <span className="text-blue-400 animate-pulse">Running...</span>}
          </div>
          <div className={`p-4 font-mono text-sm overflow-y-auto h-full whitespace-pre-wrap ${
            isTerminalError ? 'text-red-400' : 'text-green-400'
          }`}>
            {terminalOutput}
          </div>
        </div>

      </div>

      {/* MITAD DERECHA: Chat tutor ia */}
      <div className="w-1/2 h-full">
        <ChatPanel 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          isLoading={isAiTyping} 
          onClearChat={() => setMessages([])}
        />
      </div>

    </div>
  );
}