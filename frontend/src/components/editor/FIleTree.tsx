import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileCode, Folder, FolderOpen } from 'lucide-react';

interface FileTreeProps {
  files: string[];
  activeFile: string;
  onSelectFile: (path: string) => void;
}

const buildTree = (paths: string[]) => {
  const tree: any = {};
  paths.forEach(path => {
    const parts = path.split('/');
    let current = tree;
    parts.forEach((part, i) => {
      if (!current[part]) {
        current[part] = i === parts.length - 1 ? null : {};
      }
      current = current[part];
    });
  });
  return tree;
};

const TreeItem = ({ name, node, path, activeFile, onSelectFile, level }: any) => {
  const [isOpen, setIsOpen] = useState(true);
  const isFolder = node !== null;
  const currentPath = path ? `${path}/${name}` : name;
  const isActive = activeFile === currentPath;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isFolder) {
      setIsOpen(!isOpen);
    } else {
      onSelectFile(currentPath);
    }
  };

  return (
    <div>
      <div 
        onClick={handleClick}
        className={`flex items-center gap-1.5 py-1 px-2 cursor-pointer transition-all duration-150 rounded-sm mx-1 my-[1px]
          ${isActive ? 'bg-blue-600/20 text-blue-400 border-l-2 border-blue-500' : 'text-gray-400 hover:bg-gray-800'}`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        {isFolder ? (
          <>
            {isOpen ? <ChevronDown size={14} className="shrink-0" /> : <ChevronRight size={14} className="shrink-0" />}
            {isOpen ? <FolderOpen size={16} className="text-yellow-500 shrink-0" /> : <Folder size={16} className="text-yellow-500 shrink-0" />}
          </>
        ) : (
          <FileCode size={16} className={`${isActive ? 'text-blue-400' : 'text-gray-500'} shrink-0`} />
        )}
        <span className="text-[13px] truncate font-medium">{name}</span>
      </div>

      {isFolder && isOpen && (
        <div className="overflow-hidden">
          {Object.entries(node).map(([childName, childNode]) => (
            <TreeItem 
              key={childName} 
              name={childName} 
              node={childNode} 
              path={currentPath} 
              activeFile={activeFile}
              onSelectFile={onSelectFile}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default function FileTree({ files, activeFile, onSelectFile }: FileTreeProps) {
  const tree = buildTree(files);

  return (
    <div className="py-2 overflow-y-auto h-full scrollbar-hide">
      {Object.entries(tree).length === 0 ? (
        <div className="px-4 py-2 text-xs text-gray-500 italic text-center">No hay archivos</div>
      ) : (
        Object.entries(tree)
          .sort(([a, nodeA], [b, nodeB]) => {
            // Ordenar: Carpetas primero, luego archivos
            const isFolderA = nodeA !== null;
            const isFolderB = nodeB !== null;
            if (isFolderA && !isFolderB) return -1;
            if (!isFolderA && isFolderB) return 1;
            return a.localeCompare(b);
          })
          .map(([name, node]) => (
            <TreeItem 
              key={name} 
              name={name} 
              node={node} 
              path="" 
              activeFile={activeFile}
              onSelectFile={onSelectFile}
              level={0}
            />
          ))
      )}
    </div>
  );
}