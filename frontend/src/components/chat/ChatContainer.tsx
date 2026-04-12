import { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useConversationStore } from '../../store/conversationStore';
import type { Product, IntentData } from '../../types';

export function ChatContainer() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    messages,
    isLoading,
    loadingText,
    sendMessage,
    selectProduct,
  } = useConversationStore();

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = (text: string) => {
    sendMessage(text);
  };

  const handleSelectProduct = (product: Product) => {
    // 找到最近的意图数据（简化处理）
    const lastAnalyzeMessage = [...messages]
      .reverse()
      .find((m) => m.type === 'text' && m.role === 'assistant');

    if (lastAnalyzeMessage) {
      const intentData: IntentData = {
        intent: 'analyze',
        brand: '',
        product: product.name,
        needXiaohongshu: false,
        needHeimao: false,
        needTaobao: true,
        clarificationNeeded: false,
        clarificationQuestion: '',
        response: '',
      };
      selectProduct(product, intentData);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mb-4">
              <svg
                className="w-8 h-8 text-primary-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              欢迎使用避雷真
            </h3>
            <p className="text-sm max-w-md">
              我可以帮你分析商品口碑、识别虚假好评、对比不同商品。
              <br />
              试着问我："帮我分析德芙巧克力"
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onSelectProduct={handleSelectProduct}
            />
          ))
        )}

        {/* Loading indicator for async operations */}
        {isLoading && loadingText && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
            <span>{loadingText}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <ChatInput
        onSend={handleSendMessage}
        isLoading={isLoading}
        placeholder="输入消息，例如：帮我分析德芙巧克力..."
      />
    </div>
  );
}
