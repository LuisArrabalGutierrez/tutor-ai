import { useState } from 'react';
import JSZip from 'jszip';

const INITIAL_CODE = `#include <iostream>\n\nint main() {\n    std::cout << "¡Hola Mundo desde mi propio IDE!" << std::endl;\n    return 0;\n}`;
const VALID_EXTENSIONS = ['.cpp', '.h', '.hpp', '.c', '.txt', '.csv', '.json'];

{/* Hook personalizado para manejar la lógica del proyecto, incluyendo el estado de los archivos del proyecto, 
  el archivo activo, la función para manejar la subida de carpetas, la función para descargar el proyecto como zip,
   la función para manejar los cambios en el editor, y la función para obtener el lenguaje de programación de un archivo */ }
export function useProject() {
  const [projectFiles, setProjectFiles] = useState<Record<string, string>>({
    "main.cpp": INITIAL_CODE
  });
  const [activeFile, setActiveFile] = useState<string>("main.cpp");

    {/* Función para manejar la subida de carpetas, que lee los archivos seleccionados por el usuario,
    filtra los archivos válidos, actualiza el estado de los archivos del proyecto y el archivo activo,
    y luego limpia el input de archivos para permitir nuevas subidas sin problemas */ }
  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>, onSuccess?: () => void) => {
    const files = event.target.files;
    if (!files) return;

    const newFilesDict: Record<string, string> = {};
    let firstCppFile = "";

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const name = file.name.toLowerCase();
      
      // lgica de filtrado refactorizada para mayor claridad
      const isHidden = file.webkitRelativePath.includes('.git/');
      const isValidExt = VALID_EXTENSIONS.some(ext => name.endsWith(ext)) || name === 'makefile';

      if (!isValidExt || isHidden) continue;

      // Lee el contenido del archivo y construye la ruta limpia sin la parte de la carpeta raíz
      const text = await file.text();
      const pathParts = file.webkitRelativePath.split('/');
      pathParts.shift(); 
      const cleanPath = pathParts.join('/') || file.name;
      
      // Agrega el archivo al nuevo diccionario de archivos del proyecto
      newFilesDict[cleanPath] = text;
      if (!firstCppFile && cleanPath.endsWith('.cpp')) firstCppFile = cleanPath;
    }

    // Si se han encontrado archivos válidos, actualiza el estado del proyecto y el archivo activo, y llama a la función de éxito si se proporciona
    if (Object.keys(newFilesDict).length > 0) {
      setProjectFiles(newFilesDict);
      setActiveFile(firstCppFile || Object.keys(newFilesDict)[0]);
      onSuccess?.();
    }
    event.target.value = '';
  };

  {/* Función para manejar la descarga del proyecto como un archivo zip, que utiliza la biblioteca JSZip para crear un archivo zip en el cliente,
  agrega los archivos del proyecto al zip, genera un blob del zip, crea una URL para el blob, y luego simula un clic en un enlace de descarga para descargar el archivo zip */ }
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

    {/* Función para manejar los cambios en el editor, que actualiza el estado de los archivos del proyecto con el nuevo contenido del archivo activo */ }
  const handleEditorChange = (newValue: string | undefined) => {
    if (newValue !== undefined) {
      setProjectFiles(prev => ({ ...prev, [activeFile]: newValue }));
    }
  };

    {/* Función para obtener el lenguaje de programación de un archivo, 
      que se basa en la extensión del archivo para determinar el lenguaje y 
      devuelve una cadena que representa el lenguaje (por ejemplo, "cpp" para archivos C++ y "json" para archivos JSON) */ }
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