import { Files } from 'lucide-react';
import FileTree from './FIleTree.tsx';

interface SidebarProps {
  files: string[];
  activeFile: string;
  onSelectFile: (path: string) => void;
}

export default function Sidebar({ files, activeFile, onSelectFile }: SidebarProps) {
  return (
    <div className="w-1/4 h-full bg-[#181818] border-r border-[#2d2d2d] flex flex-col shrink-0 overflow-hidden">
      <div className="p-3 border-b border-[#2d2d2d] bg-[#1e1e1e]">
        <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
          <Files size={14} /> EXPLORADOR
        </h2>
      </div>
      
      <div className="flex-grow overflow-y-auto">
        <FileTree 
          files={files} 
          activeFile={activeFile} 
          onSelectFile={onSelectFile} 
        />
      </div>
    </div>
  );
}