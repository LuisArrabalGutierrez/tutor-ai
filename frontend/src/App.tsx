// Ruta: src/App.tsx
import { useState } from 'react';
import CodeEditor from './components/editor/CodeEditor';
import ChatPanel from './components/chat/ChatPanel';
import TopBar from './components/layout/TopBar';
import Sidebar from './components/editor/SideBar';
import TerminalPanel from './components/editor/Terminal';
import { FileCode } from 'lucide-react';

import { useProject } from './hooks/useProject';
import { useChat } from './hooks/UseChat';
import { useTerminal } from './hooks/useTerminal';
import LinuxTerminal from './components/editor/LinuxTerminal';
import type { Asignatura } from './types';

{/* Componente principal de la aplicación, que maneja la estructura general de la interfaz, el estado de la asignatura seleccionada,
   la visibilidad del chat, y coordina los diferentes componentes y hooks para el editor de código, el chat y el terminal */ } 
export default function App() {

  {/* Estado para controlar la visibilidad del chat, la asignatura seleccionada y el contexto del terminal */}
  const [isChatOpen, setIsChatOpen] = useState(true);
  {/* Estado para controlar la asignatura, que por defecto es C++ */}
  const [asignatura, setAsignatura] = useState<Asignatura>('cpp');

  const [terminalContext, setTerminalContext] = useState("");

  {/* Hooks personalizados para manejar la lógica del proyecto, el chat y el terminal */}
  const { projectFiles, activeFile, setActiveFile, handleFolderUpload, handleDownloadZip, handleEditorChange, getLang } = useProject();

  {/* Hooks para usar la logica de  la terminal y/o compilador usando los archivos subidos como parametro*/}
  const { terminalOutput, isCompiling, isTerminalError, handleRunCode, setTerminalMessage } = useTerminal(projectFiles);

  {/* Hook para manejar la lógica del chat, pasando los archivos del proyecto para que el asistente pueda analizarlos y responder */}
  const { messages, isAiTyping, handleSendMessage, clearChat } = useChat(projectFiles);

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-gray-200 font-sans overflow-hidden">
      <div className={`h-full flex flex-col border-r border-gray-700 transition-all duration-500 ${isChatOpen ? 'w-1/2' : 'w-full'}`}>

        {/* El "header" donde estan los botones de subir archivo,etc */}
        <TopBar 
          asignaturaActual={asignatura}
          onCambiarAsignatura={setAsignatura}
          onUpload={(e) => handleFolderUpload(e, () => setTerminalMessage("✅ Proyecto cargado."))} 
          onDownload={handleDownloadZip} 
          onRun={handleRunCode} 
          isCompiling={isCompiling} 
          isChatOpen={isChatOpen} 
          toggleChat={() => setIsChatOpen(!isChatOpen)} 
        />
        
        {/* El area principal, que se divide en dos partes: el sidebar con los archivos y el editor/terminal o la terminal de linux dependiendo de la asignatura */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {asignatura === 'cpp' ? (
            <div className="flex flex-col h-full">
              <div className="flex-grow h-[70%] flex">
                <Sidebar files={Object.keys(projectFiles)} activeFile={activeFile} onSelectFile={setActiveFile} />
                <div className="w-3/4 h-full relative bg-[#1e1e1e]">
                  <div className="absolute top-0 left-0 bg-[#1e1e1e] text-gray-300 text-xs font-mono px-4 py-2 z-10 flex items-center gap-2 border-b border-r border-[#2d2d2d]">
                    <FileCode size={14} className="text-blue-400" /> {activeFile}
                  </div>
                  <div className="pt-8 h-full">
                    <CodeEditor code={projectFiles[activeFile] || ""} onChange={handleEditorChange} language={getLang(activeFile)} />
                  </div>
                </div>
              </div>
              <div className="h-[30%]">
                <TerminalPanel output={terminalOutput} isError={isTerminalError} />
              </div>
            </div>
          ) : (
            <div className="w-full h-full bg-[#1e1e1e]">
              <LinuxTerminal onTerminalOutputChange={setTerminalContext} />
            </div>
          )}
        </div>
      </div>

      {/* El panel de chat, que se muestra u oculta dependiendo del estado isChatOpen con esto: ${isChatOpen ? 'w-1/2' : 'w-0 overflow-hidden'} */}

      <div className={`h-full bg-gray-950 transition-all duration-500 flex-shrink-0 ${isChatOpen ? 'w-1/2' : 'w-0 overflow-hidden'}`}>
          <ChatPanel 
            messages={messages} 
            onSendMessage={(msg) => handleSendMessage(msg, asignatura, terminalContext)} 
            isLoading={isAiTyping} 
            onClearChat={clearChat} 
          />
      </div>
    </div>
  );
}