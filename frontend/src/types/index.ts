export interface CodeEditorProps {
    code: string;
    onChange: (value: string | undefined) => void;
    language?: string;
  }


export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}