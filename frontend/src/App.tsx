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

export type Asignatura = 'cpp' | 'linux';

export default function App() {
  const [isChatOpen, setIsChatOpen] = useState<boolean>(true);
  const [asignatura, setAsignatura] = useState<Asignatura>('cpp');
  const [terminalContext, setTerminalContext] = useState<string>("");

  // Instanciamos los hooks
  const { projectFiles, activeFile, setActiveFile, handleFolderUpload, handleDownloadZip, handleEditorChange, getLang } = useProject();
  const { terminalOutput, isCompiling, isTerminalError, handleRunCode, setTerminalMessage } = useTerminal(projectFiles);
  const { messages, isAiTyping, handleSendMessage, clearChat } = useChat(projectFiles);

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-gray-200 font-sans overflow-hidden">
      
      {/* MITAD IZQUIERDA: Entorno de Trabajo */}
      <div className={`h-full flex flex-col border-r border-gray-700 transition-all duration-500 ${isChatOpen ? 'w-1/2' : 'w-full'}`}>
        <TopBar 
          asignaturaActual={asignatura}
          onCambiarAsignatura={(nueva) => setAsignatura(nueva as Asignatura)}
          onUpload={(e) => handleFolderUpload(e, () => setTerminalMessage("✅ Proyecto cargado."))} 
          onDownload={handleDownloadZip} 
          onRun={handleRunCode} 
          isCompiling={isCompiling} 
          isChatOpen={isChatOpen} 
          toggleChat={() => setIsChatOpen(!isChatOpen)} 
        />
        
        <div className="flex-1 overflow-hidden flex flex-col">
          {asignatura === 'cpp' ? (
            <>
              {/* VISTA C++: Editor + Terminal de Compilación */}
              <div className="flex-grow h-[70%] flex">
                <Sidebar files={Object.keys(projectFiles)} activeFile={activeFile} onSelectFile={setActiveFile} />
                
                <div className="w-3/4 h-full relative">
                  <div className="absolute top-0 left-0 bg-[#1e1e1e] text-gray-300 text-xs font-mono px-4 py-2 z-10 flex items-center gap-2 border-b border-r border-[#2d2d2d]">
                    <FileCode size={14} className="text-blue-400" /> {activeFile}
                  </div>
                  <div className="pt-8 h-full bg-[#1e1e1e]">
                    <CodeEditor 
                      code={projectFiles[activeFile] || ""} 
                      onChange={handleEditorChange} 
                      language={getLang(activeFile)} 
                    />
                  </div>
                </div>
              </div>
              
              <div className="h-[30%]">
                <TerminalPanel output={terminalOutput} isError={isTerminalError} />
              </div>
            </>
          ) : (
            /* VISTA LINUX: Terminal Interactiva a pantalla completa */
            <div className="w-full h-full bg-[#1e1e1e]">
              <LinuxTerminal onTerminalOutputChange={setTerminalContext} />
            </div>
          )}
        </div>
      </div>

      {/* MITAD DERECHA: Chat */}
      <div className={`h-full bg-gray-950 transition-all duration-500 flex-shrink-0 ${isChatOpen ? 'w-1/2 translate-x-0' : 'w-0 translate-x-full overflow-hidden'}`}>
        <div className="w-full h-full min-w-[300px]">
          <ChatPanel 
            messages={messages} 
            // Inyectamos la asignatura y el texto de la terminal cada vez que el alumno envía un mensaje
            onSendMessage={(msg) => handleSendMessage(msg, asignatura, terminalContext)} 
            isLoading={isAiTyping} 
            onClearChat={clearChat} 
          />
        </div>
      </div>

    </div>
  );
}