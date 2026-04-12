import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { Sidebar } from './components/layout/Sidebar';
import { ChatContainer } from './components/chat/ChatContainer';
import { HelpModal } from './components/layout/HelpModal';
import useConversationStore from './store/conversationStore';

function App() {
  const { sessionId } = useConversationStore();
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar currentSessionId={sessionId} />

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
            <div className="text-sm text-gray-500">
              对话式商品口碑分析助手
            </div>
          </div>
        </header>

        {/* Help Modal */}
        <HelpModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />

        {/* Chat Area */}
        <main className="flex-1 overflow-hidden">
          <ChatContainer />
        </main>
      </div>
    </div>
  );
}

export default App;
