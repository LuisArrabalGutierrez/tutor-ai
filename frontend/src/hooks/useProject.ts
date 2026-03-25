import { useState } from 'react';
import JSZip from 'jszip';

export function useProject() {
  const [projectFiles, setProjectFiles] = useState<Record<string, string>>({
    "main.cpp": "#include <iostream>\n\nint main() {\n    std::cout << \"¡Hola Mundo desde mi propio IDE!\" << std::endl;\n    return 0;\n}"
  });
  const [activeFile, setActiveFile] = useState<string>("main.cpp");

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>, onSuccess?: () => void) => {
    const files = event.target.files;
    if (!files) return;

    const newFilesDict: Record<string, string> = {};
    let firstCppFile = "";
    const validExts = ['.cpp', '.h', '.hpp', '.c', '.txt', '.csv', '.json'];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const name = file.name.toLowerCase();
      if ((!validExts.some(ext => name.endsWith(ext)) && name !== 'makefile') || file.webkitRelativePath.includes('.git/')) continue;

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
      if (onSuccess) onSuccess();
    }
    
    // Limpiamos el input directamente desde el evento
    event.target.value = '';
  };

  const handleDownloadZip = async () => {
    const zip = new JSZip();
    Object.entries(projectFiles).forEach(([path, content]) => zip.file(path, content));
    const url = URL.createObjectURL(await zip.generateAsync({ type: "blob" }));
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

  const getLang = (f: string) => f.endsWith('.cpp') || f.endsWith('.h') ? 'cpp' : 'plaintext';

  return { projectFiles, activeFile, setActiveFile, handleFolderUpload, handleDownloadZip, handleEditorChange, getLang };
}