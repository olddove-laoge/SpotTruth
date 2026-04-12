import { Sidebar } from './components/layout/Sidebar';
import { ChatContainer } from './components/chat/ChatContainer';
import useConversationStore from './store/conversationStore';

function App() {
  const { sessionId } = useConversationStore();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar currentSessionId={sessionId} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🤖</span>
            <h1 className="font-semibold text-gray-800">避雷真</h1>
            <span className="text-xs px-2 py-0.5 bg-primary-100 text-primary-600 rounded-full">
              Beta
            </span>
          </div>
          <div className="text-sm text-gray-500">
            对话式商品口碑分析助手
          </div>
        </header>

        {/* Chat Area */}
        <main className="flex-1 overflow-hidden">
          <ChatContainer />
        </main>
      </div>
    </div>
  );
}

export default App;
