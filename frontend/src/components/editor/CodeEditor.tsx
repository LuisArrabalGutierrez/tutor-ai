import Editor from '@monaco-editor/react';
import type { CodeEditorProps } from '../../types/index.ts';

export default function CodeEditor({ code, onChange, language = 'cpp' }: CodeEditorProps) {
  return (
    <div className="flex-grow h-full w-full">
      <Editor
        height="100%"
        defaultLanguage={language}
        theme="vs-dark"
        value={code}
        onChange={onChange}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          wordWrap: 'on',
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}