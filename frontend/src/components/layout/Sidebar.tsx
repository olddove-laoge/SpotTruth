import { useEffect, useState } from 'react';
import { Plus, MessageSquare, Settings, Trash2, Edit2, Check, X, Bookmark } from 'lucide-react';
import { Button } from '../ui/Button';
import useConversationStore from '../../store/conversationStore';

interface SidebarProps {
  currentSessionId: string;
  onSettingsClick?: () => void;
  onSavedCardsClick?: () => void;
}

export function Sidebar({ currentSessionId, onSettingsClick, onSavedCardsClick }: SidebarProps) {
  const [sessions, setSessions] = useState<{ id: string; preview: string; customName?: string; timestamp: number }[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const { newSession, loadSession, deleteSession, renameSession, getSavedSessions } = useConversationStore();

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

  // 监听会话保存事件，刷新列表
  useEffect(() => {
    const handleSessionSaved = () => {
      refreshSessions();
    };
    window.addEventListener('session-saved', handleSessionSaved);
    return () => window.removeEventListener('session-saved', handleSessionSaved);
  }, []);

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

  // 开始编辑会话名称
  const startEdit = (session: { id: string; preview: string; customName?: string }) => {
    setEditingId(session.id);
    setEditName(session.customName || session.preview);
  };

  // 保存新名称
  const saveEdit = (sessionId: string) => {
    if (editName.trim()) {
      renameSession(sessionId, editName.trim());
      refreshSessions();
    }
    setEditingId(null);
    setEditName('');
  };

  // 取消编辑
  const cancelEdit = () => {
    setEditingId(null);
    setEditName('');
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
          variant="primary"
          className="w-full justify-center gap-2 bg-blue-600 text-white hover:bg-blue-700"
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
                  {editingId === session.id ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            saveEdit(session.id);
                          } else if (e.key === 'Escape') {
                            cancelEdit();
                          }
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="flex-1 text-sm px-1 py-0.5 border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                        autoFocus
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          saveEdit(session.id);
                        }}
                        className="p-0.5 hover:bg-green-100 rounded text-green-600"
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelEdit();
                        }}
                        className="p-0.5 hover:bg-red-100 rounded text-red-600"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="text-sm truncate">{session.customName || session.preview}</div>
                      <div className="text-xs text-gray-400">{formatTime(session.timestamp)}</div>
                    </>
                  )}
                </div>
                {editingId !== session.id && (
                  <>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        startEdit(session);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-blue-100 rounded transition-all"
                    >
                      <Edit2 size={14} className="text-blue-500" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSession(session.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all"
                    >
                      <Trash2 size={14} className="text-red-500" />
                    </button>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 space-y-2">
        <button
          onClick={onSavedCardsClick}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors w-full"
        >
          <Bookmark size={18} />
          <span className="text-sm">保存的卡片</span>
        </button>
        <button
          onClick={onSettingsClick}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors w-full"
        >
          <Settings size={18} />
          <span className="text-sm">设置</span>
        </button>
      </div>
    </div>
  );
}
