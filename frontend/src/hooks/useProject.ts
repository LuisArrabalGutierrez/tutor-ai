import { useState, useEffect } from 'react';
import JSZip from 'jszip';

const INITIAL_CODE = `#include <iostream>\n\nint main() {\n    std::cout << "¡Hola Mundo desde mi propio IDE!" << std::endl;\n    return 0;\n}`;
const VALID_EXTENSIONS = ['.cpp', '.h', '.hpp', '.c', '.txt', '.csv', '.json', 'makefile', '.md'];
const STORAGE_KEY = 'tutor_ai_project_files_v2';

export function useProject() {
  const [projectFiles, setProjectFiles] = useState<Record<string, string>>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error("Error cargando archivos", e);
      }
    }
    return { "main.cpp": INITIAL_CODE };
  });

  const [activeFile, setActiveFile] = useState<string>(() => {
    return Object.keys(projectFiles)[0] || "main.cpp";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projectFiles));
  }, [projectFiles]);

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>, onSuccess?: () => void) => {
    const files = event.target.files;
    if (!files) return;

    const newFilesDict: Record<string, string> = {};
    let firstEligibleFile = "";

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // webkitRelativePath nos da la ruta completa (ej: "mi_proyecto/src/main.cpp")
      // Quitamos el primer segmento (nombre de la carpeta subida) para que la raíz sea el proyecto
      const pathParts = file.webkitRelativePath.split('/');
      const relativePath = pathParts.slice(1).join('/'); 
      
      const fileName = file.name.toLowerCase();
      const hasValidExt = VALID_EXTENSIONS.some(ext => fileName.endsWith(ext)) || fileName === 'makefile';

      if (hasValidExt) {
        const text = await file.text();
        // Si el path queda vacío (archivo en raíz), usamos el nombre directamente
        const finalPath = relativePath || file.name;
        newFilesDict[finalPath] = text;

        if (!firstEligibleFile && (finalPath.endsWith('.cpp') || finalPath.endsWith('.c'))) {
          firstEligibleFile = finalPath;
        }
      }
    }

    if (Object.keys(newFilesDict).length > 0) {
      setProjectFiles(newFilesDict);
      setActiveFile(firstEligibleFile || Object.keys(newFilesDict)[0]);
      if (onSuccess) onSuccess();
    }
  };

  const handleDownloadZip = async () => {
    const zip = new JSZip();
    Object.entries(projectFiles).forEach(([path, content]) => {
      zip.file(path, content);
    });
    const blob = await zip.generateAsync({ type: "blob" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "proyecto_tutor_ai.zip";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleEditorChange = (newValue: string | undefined) => {
    if (newValue !== undefined) {
      setProjectFiles(prev => ({ ...prev, [activeFile]: newValue }));
    }
  };

  const getLang = (path: string) => {
    const ext = path.split('.').pop()?.toLowerCase();
    if (ext === 'cpp' || ext === 'h' || ext === 'hpp' || ext === 'c') return 'cpp';
    if (ext === 'json') return 'json';
    return 'plaintext';
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