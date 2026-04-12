import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { ComparisonTable } from './ComparisonTable';
import { MarkdownRenderer } from '../ui/MarkdownRenderer';
import type { ComparisonResult } from '../../types';

interface ComparisonCardProps {
  result: ComparisonResult;
}

export function ComparisonCard({ result }: ComparisonCardProps) {
  const { productA, productB, conclusion } = result;

  return (
    <Card className="w-full max-w-3xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <span>📊</span>
          对比报告
        </CardTitle>
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
