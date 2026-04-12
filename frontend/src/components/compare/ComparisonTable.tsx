import { ThumbsUp, ThumbsDown, AlertTriangle, MessageCircle } from 'lucide-react';
import type { ComparisonProduct } from '../../types';

interface ComparisonTableProps {
  productA: ComparisonProduct;
  productB: ComparisonProduct;
}

export function ComparisonTable({ productA, productB }: ComparisonTableProps) {
  const hasTaobaoA = productA.statistics.total > 0;
  const hasTaobaoB = productB.statistics.total > 0;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-3 px-4 font-medium text-gray-500">对比项</th>
            <th className="text-center py-3 px-4 font-medium text-gray-900">{productA.name}</th>
            <th className="text-center py-3 px-4 font-medium text-gray-900">{productB.name}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {/* Taobao Comments */}
          {hasTaobaoA || hasTaobaoB ? (
            <>
              <tr>
                <td className="py-3 px-4 text-gray-600 flex items-center gap-2">
                  <MessageCircle size={14} />
                  淘宝评论数
                </td>
                <td className="text-center py-3 px-4">{productA.statistics.total}</td>
                <td className="text-center py-3 px-4">{productB.statistics.total}</td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-gray-600 flex items-center gap-2">
                  <ThumbsUp size={14} className="text-emerald-500" />
                  好评率
                </td>
                <td className="text-center py-3 px-4">
                  {hasTaobaoA ? `${(productA.statistics.positiveRate * 100).toFixed(0)}%` : '-'}
                </td>
                <td className="text-center py-3 px-4">
                  {hasTaobaoB ? `${(productB.statistics.positiveRate * 100).toFixed(0)}%` : '-'}
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-gray-600 flex items-center gap-2">
                  <ThumbsDown size={14} className="text-red-500" />
                  差评率
                </td>
                <td className="text-center py-3 px-4">
                  {hasTaobaoA ? `${(productA.statistics.negativeRate * 100).toFixed(0)}%` : '-'}
                </td>
                <td className="text-center py-3 px-4">
                  {hasTaobaoB ? `${(productB.statistics.negativeRate * 100).toFixed(0)}%` : '-'}
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-gray-600 flex items-center gap-2">
                  <AlertTriangle size={14} className="text-amber-500" />
                  虚假好评
                </td>
                <td className="text-center py-3 px-4">{productA.statistics.sarcasmCount}条</td>
                <td className="text-center py-3 px-4">{productB.statistics.sarcasmCount}条</td>
              </tr>
            </>
          ) : null}

          {/* Xiaohongshu */}
          {(productA.xhsCount > 0 || productB.xhsCount > 0) && (
            <tr>
              <td className="py-3 px-4 text-gray-600">📱 小红书笔记</td>
              <td className="text-center py-3 px-4">{productA.xhsCount > 0 ? `${productA.xhsCount}条` : '-'}</td>
              <td className="text-center py-3 px-4">{productB.xhsCount > 0 ? `${productB.xhsCount}条` : '-'}</td>
            </tr>
          )}

          {/* Heimao */}
          {(productA.heimaoCount > 0 || productB.heimaoCount > 0) && (
            <tr>
              <td className="py-3 px-4 text-gray-600">⚠️ 黑猫投诉</td>
              <td className="text-center py-3 px-4">{productA.heimaoCount > 0 ? `${productA.heimaoCount}条` : '-'}</td>
              <td className="text-center py-3 px-4">{productB.heimaoCount > 0 ? `${productB.heimaoCount}条` : '-'}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
