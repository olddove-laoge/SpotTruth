import { motion } from 'framer-motion';
import { User, Bot, AlertCircle } from 'lucide-react';
import type { Message } from '../../types';
import { AnalysisCard } from '../analysis/AnalysisCard';
import { ProductSelectCard } from '../product/ProductSelectCard';
import { ComparisonCard } from '../compare/ComparisonCard';

interface ChatMessageProps {
  message: Message;
  onSelectProduct?: (product: any) => void;
}

export function ChatMessage({ message, onSelectProduct }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-primary-500 text-white'
            : message.type === 'error'
            ? 'bg-red-100 text-red-600'
            : 'bg-gray-100 text-gray-600'
        }`}
      >
        {isUser ? (
          <User size={16} />
        ) : message.type === 'error' ? (
          <AlertCircle size={16} />
        ) : (
          <Bot size={16} />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        {/* Text/Loading/Error Message */}
        {(message.type === 'text' || message.type === 'error') && (
          <div
            className={`inline-block max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
              isUser
                ? 'bg-primary-500 text-white'
                : message.type === 'error'
                ? 'bg-red-50 text-red-700 border border-red-200'
                : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
            }`}
          >
            {message.content}
          </div>
        )}

        {/* Loading Message */}
        {message.type === 'loading' && (
          <div className="inline-flex items-center gap-2 bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
            <div className="loading-dots text-primary-500">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="text-sm text-gray-600">{message.content}</span>
          </div>
        )}

        {/* Product Select Card */}
        {message.type === 'product_select' && message.metadata?.products && (
          <div className="mt-2">
            <ProductSelectCard
              products={message.metadata.products}
              onSelect={onSelectProduct || (() => {})}
            />
          </div>
        )}

        {/* Analysis Report Card */}
        {message.type === 'analysis_report' && message.metadata?.analysisResult && (
          <div className="mt-2 max-w-2xl">
            <AnalysisCard result={message.metadata.analysisResult} />
          </div>
        )}

        {/* Comparison Report Card */}
        {message.type === 'comparison_report' && message.metadata?.comparisonResult && (
          <div className="mt-2 max-w-3xl">
            <ComparisonCard result={message.metadata.comparisonResult} />
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-1 text-xs text-gray-400">
          {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </motion.div>
  );
}
