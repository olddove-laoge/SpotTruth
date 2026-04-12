import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 自定义标题样式
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-gray-800 mt-4 mb-2">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold text-gray-800 mt-3 mb-2">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold text-gray-800 mt-2 mb-1">{children}</h3>
          ),
          // 自定义段落样式
          p: ({ children }) => (
            <p className="text-sm text-gray-700 leading-relaxed mb-2">{children}</p>
          ),
          // 自定义列表样式
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-gray-700">{children}</li>
          ),
          // 自定义加粗样式
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-900">{children}</strong>
          ),
          // 自定义代码样式
          code: ({ children }) => (
            <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">
              {children}
            </code>
          ),
          // 自定义引用样式
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-gray-300 pl-3 py-1 my-2 bg-gray-50">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
