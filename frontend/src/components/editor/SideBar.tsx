import { FolderOpen, FileCode } from 'lucide-react';

interface SidebarProps {
  files: string[];
  activeFile: string;
  onSelectFile: (filename: string) => void;
}

export default function Sidebar({ files, activeFile, onSelectFile }: SidebarProps) {
  return (
    <div className="w-1/4 bg-[#181818] border-r border-gray-800 flex flex-col">
      <div className="text-[10px] uppercase font-bold text-gray-500 p-3 tracking-wider flex items-center gap-2">
        <FolderOpen size={12} />
        Archivos ({files.length})
      </div>
      <div className="overflow-y-auto flex-grow py-1">
        {files.map((filename) => (
          <div 
            key={filename}
            onClick={() => onSelectFile(filename)}
            className={`px-4 py-1.5 text-xs font-mono cursor-pointer truncate transition-colors flex items-center gap-2 ${
              activeFile === filename ? 'bg-blue-900/30 text-blue-300 border-l-2 border-blue-500' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 border-l-2 border-transparent'
            }`}
          >
            <FileCode size={14} className={filename.endsWith('.cpp') || filename.endsWith('.h') ? "text-blue-400" : "text-gray-500"} />
            {filename.split('/').pop()}
          </div>
        ))}
      </div>
    </div>
  );
}