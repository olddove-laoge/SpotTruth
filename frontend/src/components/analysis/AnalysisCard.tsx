import { useState } from 'react';
import { MessageSquare, Sparkles, ShoppingCart, Bookmark, BookmarkCheck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { SentimentChart } from './SentimentChart';
import { CommentList } from './CommentList';
import { useSavedCardsStore } from '../../store/savedCardsStore';
import type { AnalysisResult } from '../../types';

interface AnalysisCardProps {
  result: AnalysisResult;
}

export function AnalysisCard({ result }: AnalysisCardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'comments' | 'xhs' | 'heimao'>('overview');
  const { saveCard, isCardSaved, removeCard } = useSavedCardsStore();

  const { statistics, summary, advice, results, xiaohongshu, heimao } = result;
  const cardId = `analysis-${result.productName}`;
  const saved = isCardSaved(cardId);

  const handleSave = () => {
    if (saved) {
      removeCard(cardId);
    } else {
      saveCard({
        id: cardId,
        type: 'analysis',
        title: result.productName,
        data: result,
        timestamp: Date.now(),
      });
    }
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>📦</span>
              {result.productName}
              <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full text-gray-600">
                {result.category}
              </span>
            </CardTitle>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleSave}
            className={saved ? 'text-amber-500' : 'text-gray-400 hover:text-amber-500'}
            title={saved ? '取消保存' : '保存卡片'}
          >
            {saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-100">
          {[
            { id: 'overview', label: '概览', icon: Sparkles },
            { id: 'comments', label: '评论', icon: MessageSquare },
            ...(xiaohongshu ? [{ id: 'xhs', label: '小红书', icon: () => <span>📱</span> }] : []),
            ...(heimao ? [{ id: 'heimao', label: '黑猫', icon: () => <span>⚠️</span> }] : []),
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* Statistics */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-blue-600">{statistics.total}</div>
                <div className="text-xs text-blue-600/70">总评论</div>
              </div>
              <div className="bg-emerald-50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-emerald-600">
                  {(statistics.positiveRate * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-emerald-600/70">好评率</div>
              </div>
              <div className="bg-amber-50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-amber-600">{statistics.sarcasmCount}</div>
                <div className="text-xs text-amber-600/70">虚假好评</div>
              </div>
            </div>

            {/* Sentiment Chart */}
            {statistics.total > 0 && (
              <div className="h-40">
                <SentimentChart
                  positive={statistics.positiveCount}
                  negative={statistics.negativeCount}
                />
              </div>
            )}

            {/* Summary */}
            {summary && (
              <div className="bg-gray-50 rounded-lg p-3">
                <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1.5">
                  <Sparkles size={14} className="text-primary-500" />
                  分析总结
                </h4>
                <p className="text-sm text-gray-600 leading-relaxed">{summary}</p>
              </div>
            )}

            {/* Advice */}
            {advice && (
              <div className="bg-primary-50 rounded-lg p-3 border border-primary-100">
                <h4 className="text-sm font-medium text-primary-700 mb-2 flex items-center gap-1.5">
                  <ShoppingCart size={14} />
                  购买建议
                </h4>
                <p className="text-sm text-primary-700/80 leading-relaxed">{advice}</p>
              </div>
            )}

            {/* 小红书概览 */}
            {xiaohongshu && (
              <div className="bg-pink-50 rounded-lg p-3 border border-pink-100">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-pink-700 flex items-center gap-1.5">
                    <span>📱</span>
                    小红书
                  </h4>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      xiaohongshu.sentiment === 'mostly_positive'
                        ? 'bg-emerald-100 text-emerald-700'
                        : xiaohongshu.sentiment === 'mostly_negative'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {xiaohongshu.sentiment === 'mostly_positive'
                      ? '整体正面'
                      : xiaohongshu.sentiment === 'mostly_negative'
                      ? '整体负面'
                      : '褒贬不一'}
                  </span>
                </div>
                <p className="text-sm text-pink-700/80 leading-relaxed line-clamp-3">{xiaohongshu.summary}</p>
                {xiaohongshu.keyPoints.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-pink-600/70 mb-1">关键发现：</p>
                    <ul className="space-y-0.5">
                      {xiaohongshu.keyPoints.slice(0, 3).map((point, index) => (
                        <li key={index} className="text-xs text-pink-700/70 flex items-start gap-1">
                          <span className="text-pink-400">•</span>
                          <span className="line-clamp-1">{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* 黑猫投诉概览 */}
            {heimao && (
              <div className="bg-red-50 rounded-lg p-3 border border-red-100">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-red-700 flex items-center gap-1.5">
                    <span>⚠️</span>
                    黑猫投诉
                  </h4>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      heimao.severity === 'high'
                        ? 'bg-red-100 text-red-700'
                        : heimao.severity === 'medium'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-emerald-100 text-emerald-700'
                    }`}
                  >
                    风险等级：{heimao.severity === 'high' ? '高' : heimao.severity === 'medium' ? '中' : '低'}
                  </span>
                </div>
                <p className="text-sm text-red-700/80 leading-relaxed line-clamp-2">{heimao.summary}</p>
                {heimao.complaintTypes.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {heimao.complaintTypes.slice(0, 4).map((type, index) => (
                      <span
                        key={index}
                        className="text-xs px-2 py-0.5 bg-red-100/50 text-red-600 rounded"
                      >
                        {type}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Comments Tab */}
        {activeTab === 'comments' && (
          <CommentList comments={results.slice(0, 10)} />
        )}

        {/* Xiaohongshu Tab */}
        {activeTab === 'xhs' && xiaohongshu && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  xiaohongshu.sentiment === 'mostly_positive'
                    ? 'bg-emerald-100 text-emerald-700'
                    : xiaohongshu.sentiment === 'mostly_negative'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-amber-100 text-amber-700'
                }`}
              >
                {xiaohongshu.sentiment === 'mostly_positive'
                  ? '整体正面'
                  : xiaohongshu.sentiment === 'mostly_negative'
                  ? '整体负面'
                  : '褒贬不一'}
              </span>
            </div>
            <p className="text-sm text-gray-600">{xiaohongshu.summary}</p>
            {xiaohongshu.keyPoints.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">关键发现</h5>
                <ul className="space-y-1">
                  {xiaohongshu.keyPoints.map((point, index) => (
                    <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="text-primary-500 mt-0.5">•</span>
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Heimao Tab */}
        {activeTab === 'heimao' && heimao && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  heimao.severity === 'high'
                    ? 'bg-red-100 text-red-700'
                    : heimao.severity === 'medium'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                风险等级:
                {heimao.severity === 'high' ? '高' : heimao.severity === 'medium' ? '中' : '低'}
              </span>
            </div>
            <p className="text-sm text-gray-600">{heimao.summary}</p>
            {heimao.complaintTypes.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">主要投诉类型</h5>
                <div className="flex flex-wrap gap-2">
                  {heimao.complaintTypes.map((type, index) => (
                    <span
                      key={index}
                      className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded-full"
                    >
                      {type}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {heimao.recommendation && (
              <div className="bg-amber-50 rounded-lg p-3 text-sm text-amber-800">
                <strong>建议：</strong>
                {heimao.recommendation}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
