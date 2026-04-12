import { useState } from 'react';
import { Plus, MessageSquare, Settings, Trash2 } from 'lucide-react';
import { Button } from '../ui/Button';

interface SidebarProps {
  onNewChat: () => void;
  currentSessionId: string;
}

export function Sidebar({ onNewChat, currentSessionId }: SidebarProps) {
  const [sessions, setSessions] = useState<{ id: string; title: string; date: string }[]>([
    { id: '1', title: '德芙巧克力分析', date: '今天' },
    { id: '2', title: 'iPhone 15 对比', date: '昨天' },
  ]);

  const handleDeleteSession = (id: string) => {
    setSessions(sessions.filter((s) => s.id !== id));
    localStorage.removeItem(`session_${id}`);
  };

  return (
    <div className="w-64 h-full bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <Button
          onClick={onNewChat}
          className="w-full justify-center gap-2"
        >
          <Plus size={18} />
          新对话
        </Button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="text-xs font-medium text-gray-500 mb-2 px-2">历史会话</div>
        <div className="space-y-1">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors ${
                session.id === currentSessionId
                  ? 'bg-primary-100 text-primary-700'
                  : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <MessageSquare size={16} />
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate">{session.title}</div>
                <div className="text-xs text-gray-400">{session.date}</div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all"
              >
                <Trash2 size={14} className="text-red-500" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <button className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors">
          <Settings size={18} />
          <span className="text-sm">设置</span>
        </button>
      </div>
    </div>
  );
}
