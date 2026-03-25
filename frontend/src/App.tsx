import { useState } from 'react';
import CodeEditor from './components/editor/CodeEditor';
import ChatPanel from './components/chat/ChatPanel';
import TopBar from './components/layout/TopBar';
import Sidebar from './components/editor/SideBar';
import TerminalPanel from './components/editor/Terminal';
import { FileCode } from 'lucide-react';

import { useProject } from './hooks/useProject.ts';
import { useChat } from './hooks/UseChat.ts';
import { useTerminal } from './hooks/useTerminal.ts';

export default function App() {
  const [isChatOpen, setIsChatOpen] = useState<boolean>(true);

  // Instanciamos los hooks
  const { projectFiles, activeFile, setActiveFile, handleFolderUpload, handleDownloadZip, handleEditorChange, getLang } = useProject();
  const { terminalOutput, isCompiling, isTerminalError, handleRunCode, setTerminalMessage } = useTerminal(projectFiles);
  const { messages, isAiTyping, handleSendMessage, clearChat } = useChat(projectFiles);

  return (
    <div className="flex h-screen w-screen bg-gray-900 text-gray-200 font-sans overflow-hidden">
      
      {/* MITAD IZQUIERDA: Editor y Terminal */}
      <div className={`h-full flex flex-col border-r border-gray-700 transition-all duration-500 ${isChatOpen ? 'w-1/2' : 'w-full'}`}>
        <TopBar 
          onUpload={(e) => handleFolderUpload(e, () => setTerminalMessage("✅ Proyecto cargado."))} 
          onDownload={handleDownloadZip} 
          onRun={handleRunCode} 
          isCompiling={isCompiling} 
          isChatOpen={isChatOpen} 
          toggleChat={() => setIsChatOpen(!isChatOpen)} 
        />
        
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

        <TerminalPanel output={terminalOutput} isError={isTerminalError} />
      </div>

      {/* MITAD DERECHA: Chat */}
      <div className={`h-full bg-gray-950 transition-all duration-500 flex-shrink-0 ${isChatOpen ? 'w-1/2 translate-x-0' : 'w-0 translate-x-full overflow-hidden'}`}>
        <div className="w-full h-full min-w-[300px]">
          <ChatPanel 
            messages={messages} 
            onSendMessage={handleSendMessage} 
            isLoading={isAiTyping} 
            onClearChat={clearChat} 
          />
        </div>
      </div>

    </div>
  );
}