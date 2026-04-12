import { useState, type KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, isLoading, placeholder = '输入消息...' }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="mx-auto max-w-3xl flex gap-2">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className="w-full resize-none rounded-xl border border-gray-300 bg-white px-4 py-3 pr-12 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
            style={{ minHeight: '48px', maxHeight: '120px' }}
          />
          <div className="absolute right-3 bottom-3 text-xs text-gray-400">
            {input.length > 0 && (
              <span>按 Enter 发送</span>
            )}
          </div>
        </div>
        <Button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="self-end h-12 w-12 p-0 flex items-center justify-center"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </Button>
      </div>
    </div>
  );
}
