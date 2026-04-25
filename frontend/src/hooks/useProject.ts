import { useState, useEffect } from 'react';
import JSZip from 'jszip';

const INITIAL_CODE = `#include <iostream>\n\nint main() {\n    std::cout << "¡Hola Mundo desde mi propio IDE!" << std::endl;\n    return 0;\n}`;
const VALID_EXTENSIONS = ['.cpp', '.h', '.hpp', '.c', '.txt', '.csv', '.json'];
const STORAGE_KEY = 'tutor_ai_project_files';

export function useProject() {
  // 1. Intentamos cargar los archivos guardados al iniciar el estado
  const [projectFiles, setProjectFiles] = useState<Record<string, string>>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error("Error cargando archivos del localStorage", e);
      }
    }
    // Si no hay nada guardado, cargamos el código inicial
    return { "main.cpp": INITIAL_CODE };
  });

  const [activeFile, setActiveFile] = useState<string>("main.cpp");

  // 2. Efecto para persistir los cambios automáticamente
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projectFiles));
  }, [projectFiles]);

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>, onSuccess?: () => void) => {
    const files = event.target.files;
    if (!files) return;

    const newFilesDict: Record<string, string> = {};
    let firstCppFile = "";

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      if (VALID_EXTENSIONS.includes(extension)) {
        const text = await file.text();
        newFilesDict[file.name] = text;
        if (!firstCppFile && (extension === '.cpp' || extension === '.c')) {
          firstCppFile = file.name;
        }
      }
    }

    if (Object.keys(newFilesDict).length > 0) {
      setProjectFiles(newFilesDict);
      if (firstCppFile) setActiveFile(firstCppFile);
      if (onSuccess) onSuccess();
    }
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

  return { 
    projectFiles, 
    activeFile, 
    setActiveFile, 
    handleFolderUpload, 
    handleDownloadZip, 
    handleEditorChange, 
    getLang 
  };
}