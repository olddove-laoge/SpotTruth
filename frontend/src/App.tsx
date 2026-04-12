import { useState, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';
import { Sidebar } from './components/layout/Sidebar';
import { ChatContainer } from './components/chat/ChatContainer';
import { HelpModal } from './components/layout/HelpModal';
import { SettingsModal } from './components/settings/SettingsModal';
import { Login } from './components/auth/Login';
import useConversationStore from './store/conversationStore';

function App() {
  const { sessionId } = useConversationStore();
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // 检查登录状态
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      setIsLoggedIn(true);
    }
    setIsLoading(false);
  }, []);

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = async () => {
    // 调用后端清除 cookie
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // 忽略错误
    }
    // 清除本地状态
    localStorage.removeItem('access_token');
    setIsLoggedIn(false);
    window.location.reload();
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!isLoggedIn) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar currentSessionId={sessionId} onSettingsClick={() => setIsSettingsOpen(true)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="logo" className="h-14 w-14 object-contain" />
            <h1 className="font-semibold text-gray-800">避雷真</h1>
            <span className="text-xs px-2 py-0.5 bg-primary-100 text-primary-600 rounded-full">
              Beta
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsHelpOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="使用说明"
            >
              <HelpCircle size={16} />
              <span>使用说明</span>
            </button>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              退出登录
            </button>
          </div>
        </header>

        {/* Help Modal */}
        <HelpModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />

        {/* Settings Modal */}
        <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

        {/* Chat Area */}
        <main className="flex-1 overflow-hidden">
          <ChatContainer />
        </main>
      </div>
    </div>
  );
}

export default App;
