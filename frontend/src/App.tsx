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

export default function App() {
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [asignatura, setAsignatura] = useState<Asignatura>('cpp');
  const [terminalContext, setTerminalContext] = useState("");

  const { projectFiles, activeFile, setActiveFile, handleFolderUpload, handleDownloadZip, handleEditorChange, getLang } = useProject();
  const { terminalOutput, isCompiling, isTerminalError, handleRunCode, setTerminalMessage } = useTerminal(projectFiles);
  const { messages, isAiTyping, handleSendMessage, clearChat } = useChat(projectFiles);

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-gray-200 font-sans overflow-hidden">
      <div className={`h-full flex flex-col border-r border-gray-700 transition-all duration-500 ${isChatOpen ? 'w-1/2' : 'w-full'}`}>

        <TopBar 
          asignaturaActual={asignatura}
          onCambiarAsignatura={setAsignatura}
          onUpload={(e) => handleFolderUpload(e, () => setTerminalMessage("✅ Proyecto cargado con estructura de carpetas."))} 
          onDownload={handleDownloadZip} 
          onRun={handleRunCode} 
          isCompiling={isCompiling} 
          isChatOpen={isChatOpen} 
          toggleChat={() => setIsChatOpen(!isChatOpen)} 
        />
        
        <div className="flex-1 overflow-hidden flex flex-col">
          {asignatura === 'cpp' ? (
            <div className="flex flex-col h-full">
              <div className="flex-grow h-[70%] flex">
                <Sidebar files={Object.keys(projectFiles)} activeFile={activeFile} onSelectFile={setActiveFile} />
                <div className="flex-1 h-full relative bg-[#1e1e1e]">
                  {/* Breadcrumb del archivo activo */}
                  <div className="absolute top-0 left-0 right-0 bg-[#1e1e1e] text-gray-400 text-[11px] font-mono px-4 py-2 z-10 flex items-center gap-2 border-b border-[#2d2d2d]">
                    <FileCode size={12} className="text-blue-400" /> 
                    <span className="opacity-70">{activeFile.split('/').slice(0, -1).join(' / ')}</span>
                    {activeFile.includes('/') && <span className="opacity-40">/</span>}
                    <span className="text-gray-200 font-bold">{activeFile.split('/').pop()}</span>
                  </div>
                  <div className="pt-8 h-full">
                    <CodeEditor 
                      code={projectFiles[activeFile] || ""} 
                      onChange={handleEditorChange} 
                      language={getLang(activeFile)} 
                    />
                  </div>
                </div>
              </div>
              <div className="h-[30%] border-t border-[#2d2d2d]">
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

      <div className={`h-full bg-gray-950 transition-all duration-500 flex-shrink-0 ${isChatOpen ? 'w-1/2' : 'w-0 overflow-hidden'}`}>
        <ChatPanel 
          messages={messages} 
          onSendMessage={(msg) => handleSendMessage(msg, asignatura, terminalContext)}
          onClearChat={clearChat}
          isLoading={isAiTyping}
        />
      </div>
    </div>
  );
}