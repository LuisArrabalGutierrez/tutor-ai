import { useState, useRef } from 'react';
import CodeEditor from './components/editor/CodeEditor';
import ChatPanel from './components/chat/ChatPanel';
import type { Message } from './types/index';
import { sendMessageToBackend, executeCodeBackend } from './services/api';

export default function App() {
  const [projectFiles, setProjectFiles] = useState<Record<string, string>>({
    "main.cpp": "#include <iostream>\n\nint main() {\n    std::cout << \"¡Hola Mundo desde mi propio IDE!\" << std::endl;\n    return 0;\n}"
  });
  const [activeFile, setActiveFile] = useState<string>("main.cpp");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '¡Hola! Soy tu tutor socrático. Puedes usar el botón superior para subir una carpeta con tu proyecto C++ o programar directamente aquí. ¿En qué te ayudo?',
      timestamp: Date.now(),
    }
  ]);
  const [isAiTyping, setIsAiTyping] = useState(false);

  const [terminalOutput, setTerminalOutput] = useState<string>("Sube una carpeta de proyecto o presiona 'Ejecutar Proyecto'...");
  const [isCompiling, setIsCompiling] = useState(false);
  const [isTerminalError, setIsTerminalError] = useState(false);

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    const newFilesDict: Record<string, string> = {};
    let firstCppFile = "";

    // LISTA BLANCA DE EXTENSIONES (Ignora binarios)
    const extensionesPermitidas = ['.cpp', '.h', '.hpp', '.c', '.txt', '.csv', '.json'];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileNameLower = file.name.toLowerCase();
      
      const esValido = extensionesPermitidas.some(ext => fileNameLower.endsWith(ext)) || fileNameLower === 'makefile';
      
      if (!esValido || file.webkitRelativePath.includes('.git/')) {
        continue;
      }

      const text = await file.text();
      
      const pathParts = file.webkitRelativePath.split('/');
      pathParts.shift(); 
      const cleanPath = pathParts.join('/') || file.name;

      newFilesDict[cleanPath] = text;
      
      if (!firstCppFile && cleanPath.endsWith('.cpp')) {
        firstCppFile = cleanPath;
      }
    }

    if (Object.keys(newFilesDict).length > 0) {
      setProjectFiles(newFilesDict);
      setActiveFile(firstCppFile || Object.keys(newFilesDict)[0]);
      setTerminalOutput("✅ Proyecto cargado. Archivos binarios ignorados por seguridad.");
    }
    
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleEditorChange = (newValue: string | undefined) => {
    if (newValue !== undefined) {
      setProjectFiles(prev => ({
        ...prev,
        [activeFile]: newValue
      }));
    }
  };

  const handleSendMessage = async (text: string) => {
    const newUserMsg: Message = { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() };
    const chatActualizado = [...messages, newUserMsg];
    
    setMessages(chatActualizado);
    setIsAiTyping(true);

    try {
      const historialLimpio = chatActualizado
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .map(m => ({ role: m.role, content: m.content }));

      const reply = await sendMessageToBackend(historialLimpio, projectFiles);
      
      const newAiMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: reply, timestamp: Date.now() };
      setMessages((prev) => [...prev, newAiMsg]);
    } catch (error) {
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'system', content: '❌ Error: No se pudo conectar con el servidor.', timestamp: Date.now() }]);
    } finally {
      setIsAiTyping(false);
    }
  };
  
  const handleRunCode = async () => {
    setIsCompiling(true);
    setTerminalOutput("Enviando proyecto al servidor para compilar...");
    setIsTerminalError(false);

    const result = await executeCodeBackend(projectFiles);
    
    setTerminalOutput(result.output);
    setIsTerminalError(result.isError);
    setIsCompiling(false);
  };

  const getLanguage = (filename: string) => {
    if (filename.endsWith('.h') || filename.endsWith('.cpp') || filename.endsWith('.hpp')) return 'cpp';
    if (filename.endsWith('.txt') || filename.endsWith('.csv')) return 'plaintext';
    if (filename.endsWith('.json')) return 'json';
    return 'plaintext';
  };

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-white font-sans overflow-hidden">
      
      <div className="w-1/2 h-full flex flex-col border-r border-gray-700">
        
        <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center h-[60px]">
          <div className="flex items-center gap-3">
            <input 
              type="file" 
              ref={fileInputRef}
              onChange={handleFolderUpload}
              className="hidden"
              {...{"webkitdirectory": "", "directory": ""}} 
              multiple 
            />
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-700 hover:bg-gray-600 text-white transition flex items-center gap-2 border border-gray-600 shadow-sm"
              title="Sube una carpeta completa con tu código C++"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/><path d="M12 10v6"/><path d="m9 13 3 3 3-3"/></svg>
              Subir Proyecto
            </button>
          </div>
          
          <button 
            onClick={handleRunCode}
            disabled={isCompiling}
            className={`px-4 py-1.5 rounded-md text-xs font-medium transition shadow-sm flex items-center gap-2 ${
              isCompiling 
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                : 'bg-green-600 hover:bg-green-500 text-white'
            }`}
          >
            {isCompiling ? (
              <svg className="animate-spin h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            ) : '▶'}
            {isCompiling ? 'Compilando...' : 'Ejecutar Proyecto'}
          </button>
        </div>
        
        <div className="flex-grow h-[70%] flex">
          <div className="w-1/4 bg-gray-950 border-r border-gray-800 flex flex-col">
            <div className="text-[10px] uppercase font-bold text-gray-500 p-3 tracking-wider border-b border-gray-800">
              Archivos ({Object.keys(projectFiles).length})
            </div>
            <div className="overflow-y-auto flex-grow py-2">
              {Object.keys(projectFiles).map((filename) => (
                <div 
                  key={filename}
                  onClick={() => setActiveFile(filename)}
                  className={`px-3 py-1.5 text-xs font-mono cursor-pointer truncate transition-colors ${
                    activeFile === filename 
                      ? 'bg-blue-900/40 text-blue-300 border-l-2 border-blue-500' 
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 border-l-2 border-transparent'
                  }`}
                  title={filename}
                >
                  📄 {filename.split('/').pop()}
                </div>
              ))}
            </div>
          </div>

          <div className="w-3/4 h-full relative">
            <div className="absolute top-0 left-0 bg-[#1e1e1e] text-gray-400 text-xs font-mono px-4 py-2 z-10 border-b border-r border-black flex items-center gap-2">
              <span className="text-blue-400">{'</>'}</span> {activeFile}
            </div>
            
            <div className="pt-8 h-full bg-[#1e1e1e]">
              <CodeEditor 
                code={projectFiles[activeFile] || ""} 
                onChange={handleEditorChange} 
                language={getLanguage(activeFile)}
              />
            </div>
          </div>
        </div>

        <div className="h-[30%] bg-black border-t border-gray-700 flex flex-col">
          <div className="px-4 py-1.5 bg-gray-800 border-b border-gray-700 text-xs text-gray-400 font-mono uppercase tracking-wider flex justify-between">
            <span className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
              Consola
            </span>
          </div>
          <div className={`p-4 font-mono text-sm overflow-y-auto h-full whitespace-pre-wrap ${
            isTerminalError ? 'text-red-400' : 'text-gray-300'
          }`}>
            {terminalOutput}
          </div>
        </div>

      </div>

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