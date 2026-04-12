import { useEffect, useState } from 'react';
import { Plus, MessageSquare, Settings, Trash2 } from 'lucide-react';
import { Button } from '../ui/Button';
import useConversationStore from '../../store/conversationStore';

interface SidebarProps {
  currentSessionId: string;
}

export function Sidebar({ currentSessionId }: SidebarProps) {
  const [sessions, setSessions] = useState<{ id: string; preview: string; timestamp: number }[]>([]);
  const { newSession, loadSession, deleteSession, getSavedSessions } = useConversationStore();

  // 加载会话列表
  const refreshSessions = () => {
    const savedSessions = getSavedSessions();
    setSessions(savedSessions);
  };

  // 组件挂载时加载会话列表
  useEffect(() => {
    refreshSessions();
  }, []);

  // 监听 currentSessionId 变化，刷新列表
  useEffect(() => {
    refreshSessions();
  }, [currentSessionId]);

  const handleNewChat = () => {
    newSession();
    refreshSessions();
  };

  const handleLoadSession = (sessionId: string) => {
    if (sessionId !== currentSessionId) {
      loadSession(sessionId);
    }
  };

  const handleDeleteSession = (sessionId: string) => {
    deleteSession(sessionId);
    refreshSessions();
  };

  // 格式化时间显示
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return '今天';
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className="w-64 h-full bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <Button
          onClick={handleNewChat}
          className="w-full justify-center gap-2"
        >
          <Plus size={18} />
          新对话
        </Button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="text-xs font-medium text-gray-500 mb-2 px-2 flex justify-between items-center">
          <span>历史会话</span>
          <span className="text-gray-400">{sessions.length}个</span>
        </div>
        <div className="space-y-1">
          {sessions.length === 0 ? (
            <div className="text-sm text-gray-400 text-center py-4">
              暂无历史会话
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleLoadSession(session.id)}
                className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors ${
                  session.id === currentSessionId
                    ? 'bg-blue-100 text-blue-700'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <MessageSquare size={16} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate">{session.preview}</div>
                  <div className="text-xs text-gray-400">{formatTime(session.timestamp)}</div>
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
            ))
          )}
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
