import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, Trash2, Bookmark, BarChart3, Package } from 'lucide-react';
import { Button } from '../ui/Button';
import { useSavedCardsStore, type SavedCard } from '../../store/savedCardsStore';
import { AnalysisCard } from '../analysis/AnalysisCard';
import { ComparisonCard } from '../compare/ComparisonCard';

interface SavedCardsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SavedCardsModal({ isOpen, onClose }: SavedCardsModalProps) {
  const {
    cards,
    searchQuery,
    selectedType,
    setSearchQuery,
    setSelectedType,
    removeCard,
    getFilteredCards,
    loadCards,
  } = useSavedCardsStore();

  const [viewingCard, setViewingCard] = useState<SavedCard | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadCards();
    }
  }, [isOpen, loadCards]);

  const filteredCards = getFilteredCards();

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-primary-500" />
              <h2 className="text-xl font-bold text-gray-800">保存的卡片</h2>
              <span className="text-sm text-gray-500">({cards.length})</span>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {viewingCard ? (
              /* 查看单个卡片 */
              <div className="space-y-4">
                <Button variant="outline" size="sm" onClick={() => setViewingCard(null)}>
                  ← 返回列表
                </Button>
                {viewingCard.type === 'analysis' && (
                  <AnalysisCard result={viewingCard.data as any} />
                )}
                {viewingCard.type === 'comparison' && (
                  <ComparisonCard result={viewingCard.data as any} />
                )}
              </div>
            ) : (
              /* 卡片列表 */
              <div className="space-y-4">
                {/* Search & Filter */}
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="搜索卡片..."
                      className="w-full pl-9 pr-4 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <select
                    value={selectedType}
                    onChange={(e) => setSelectedType(e.target.value as any)}
                    className="px-3 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="all">全部</option>
                    <option value="analysis">商品分析</option>
                    <option value="comparison">对比分析</option>
                  </select>
                </div>

                {/* Cards Grid */}
                {filteredCards.length === 0 ? (
                  <div className="text-center py-12 text-gray-400">
                    {cards.length === 0 ? (
                      <div>
                        <Bookmark className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>还没有保存的卡片</p>
                        <p className="text-sm mt-1">分析商品后可以点击保存按钮收藏</p>
                      </div>
                    ) : (
                      <p>没有找到匹配的卡片</p>
                    )}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredCards.map((card) => (
                      <div
                        key={card.id}
                        className="border border-gray-200 rounded-xl p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer group"
                        onClick={() => setViewingCard(card)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            {card.type === 'analysis' ? (
                              <Package className="w-4 h-4 text-blue-500" />
                            ) : (
                              <BarChart3 className="w-4 h-4 text-purple-500" />
                            )}
                            <span className="text-xs text-gray-500">
                              {card.type === 'analysis' ? '商品分析' : '对比分析'}
                            </span>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              removeCard(card.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-50 text-red-500 rounded transition-all"
                            title="删除"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        <h3 className="font-medium text-gray-800 mt-2 line-clamp-2">{card.title}</h3>

                        <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
                          <span>{formatDate(card.timestamp)}</span>
                          <span className="text-primary-500">点击查看详情 →</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
