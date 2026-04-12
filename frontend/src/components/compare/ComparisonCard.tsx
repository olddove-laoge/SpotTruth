import { Bookmark, BookmarkCheck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { ComparisonTable } from './ComparisonTable';
import { MarkdownRenderer } from '../ui/MarkdownRenderer';
import { useSavedCardsStore } from '../../store/savedCardsStore';
import type { ComparisonResult } from '../../types';

interface ComparisonCardProps {
  result: ComparisonResult;
}

export function ComparisonCard({ result }: ComparisonCardProps) {
  const { productA, productB, conclusion } = result;
  const { saveCard, isCardSaved, removeCard } = useSavedCardsStore();

  const cardId = `comparison-${productA.name}-${productB.name}`;
  const saved = isCardSaved(cardId);

  const handleSave = () => {
    if (saved) {
      removeCard(cardId);
    } else {
      saveCard({
        id: cardId,
        type: 'comparison',
        title: `${productA.name} vs ${productB.name}`,
        data: result,
        timestamp: Date.now(),
      });
    }
  };

  return (
    <Card className="w-full max-w-3xl">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <span>📊</span>
            对比报告
          </CardTitle>
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
        {/* Comparison Table */}
        <ComparisonTable productA={productA} productB={productB} />

        {/* Conclusion */}
        <div className="bg-primary-50 rounded-lg p-4 border border-primary-100">
          <h4 className="text-sm font-medium text-primary-700 mb-2">🔍 对比结论</h4>
          <div className="text-primary-700/80">
            <MarkdownRenderer content={conclusion} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
