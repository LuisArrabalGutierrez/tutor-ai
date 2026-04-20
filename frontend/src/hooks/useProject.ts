import { useState } from 'react';
import JSZip from 'jszip';

const INITIAL_CODE = `#include <iostream>\n\nint main() {\n    std::cout << "Â¡Hola Mundo desde mi propio IDE!" << std::endl;\n    return 0;\n}`;
const VALID_EXTENSIONS = ['.cpp', '.h', '.hpp', '.c', '.txt', '.csv', '.json'];

export function useProject() {
  const [projectFiles, setProjectFiles] = useState<Record<string, string>>({
    "main.cpp": INITIAL_CODE
  });
  const [activeFile, setActiveFile] = useState<string>("main.cpp");

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>, onSuccess?: () => void) => {
    const files = event.target.files;
    if (!files) return;

    const newFilesDict: Record<string, string> = {};
    let firstCppFile = "";

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const name = file.name.toLowerCase();
      
      // LÃ³gica de filtrado refactorizada para mayor claridad
      const isHidden = file.webkitRelativePath.includes('.git/');
      const isValidExt = VALID_EXTENSIONS.some(ext => name.endsWith(ext)) || name === 'makefile';

      if (!isValidExt || isHidden) continue;

      const text = await file.text();
      const pathParts = file.webkitRelativePath.split('/');
      pathParts.shift(); 
      const cleanPath = pathParts.join('/') || file.name;
      
      newFilesDict[cleanPath] = text;
      if (!firstCppFile && cleanPath.endsWith('.cpp')) firstCppFile = cleanPath;
    }

    if (Object.keys(newFilesDict).length > 0) {
      setProjectFiles(newFilesDict);
      setActiveFile(firstCppFile || Object.keys(newFilesDict)[0]);
      onSuccess?.();
    }
    event.target.value = '';
  };

  const handleDownloadZip = async () => {
    const zip = new JSZip();
    Object.entries(projectFiles).forEach(([path, content]) => zip.file(path, content));
    const blob = await zip.generateAsync({ type: "blob" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; 
    a.download = "proyecto.zip";
    a.click(); 
    URL.revokeObjectURL(url);
  };

  const handleEditorChange = (newValue: string | undefined) => {
    if (newValue !== undefined) {
      setProjectFiles(prev => ({ ...prev, [activeFile]: newValue }));
    }
  };

  const getLang = (f: string) => {
    const ext = f.split('.').pop();
    switch(ext) {
      case 'cpp': case 'h': case 'hpp': case 'c': return 'cpp';
      case 'json': return 'json';
      default: return 'plaintext';
    }
  };

  return { projectFiles, activeFile, setActiveFile, handleFolderUpload, handleDownloadZip, handleEditorChange, getLang };
}