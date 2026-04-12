import { ThumbsUp, ThumbsDown, AlertCircle } from 'lucide-react';
import type { CommentItem } from '../../types';

interface CommentListProps {
  comments: CommentItem[];
}

export function CommentList({ comments }: CommentListProps) {
  if (comments.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>暂无评论数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
      {comments.map((comment, index) => (
        <div
          key={index}
          className={`p-3 rounded-lg border ${
            comment.isSarcasm
              ? 'bg-amber-50 border-amber-200'
              : comment.sentiment === 'positive'
              ? 'bg-emerald-50 border-emerald-200'
              : 'bg-red-50 border-red-200'
          }`}
        >
          <div className="flex items-start gap-2">
            <div className="flex-shrink-0 mt-0.5">
              {comment.isSarcasm ? (
                <AlertCircle size={16} className="text-amber-500" />
              ) : comment.sentiment === 'positive' ? (
                <ThumbsUp size={16} className="text-emerald-500" />
              ) : (
                <ThumbsDown size={16} className="text-red-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700">{comment.text}</p>
              {comment.isSarcasm && comment.llmAnalysis && (
                <p className="text-xs text-amber-600 mt-1">
                  <span className="font-medium">💡 分析:</span> {comment.llmAnalysis}
                </p>
              )}
              <div className="flex items-center gap-2 mt-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    comment.isSarcasm
                      ? 'bg-amber-200 text-amber-800'
                      : comment.sentiment === 'positive'
                      ? 'bg-emerald-200 text-emerald-800'
                      : 'bg-red-200 text-red-800'
                  }`}
                >
                  {comment.isSarcasm ? '讽刺' : comment.sentiment === 'positive' ? '好评' : '差评'}
                </span>
                <span className="text-xs text-gray-400">
                  置信度: {(comment.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
