import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import type { Product } from '../../types';

interface ProductSelectCardProps {
  products: Product[];
  onSelect: (product: Product) => void;
}

export function ProductSelectCard({ products, onSelect }: ProductSelectCardProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (product: Product) => {
    setSelectedId(product.id);
    onSelect(product);
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">📦 请选择要分析的商品</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {products.map((product) => (
          <div
            key={product.id}
            className={`p-4 rounded-lg border-2 transition-all cursor-pointer ${
              selectedId === product.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
            }`}
            onClick={() => handleSelect(product)}
          >
            <div className="flex gap-4">
              {/* Product Image */}
              <div className="w-20 h-20 bg-gray-100 rounded-lg flex-shrink-0 overflow-hidden">
                {product.imageUrl ? (
                  <img
                    src={product.imageUrl}
                    alt={product.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <span className="text-2xl">📦</span>
                  </div>
                )}
              </div>

              {/* Product Info */}
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-gray-900 truncate">{product.name}</h4>
                <div className="mt-1 flex items-center gap-3 text-sm">
                  <span className="text-red-600 font-semibold">{product.price}</span>
                  {product.sales && (
                    <span className="text-gray-500">{product.sales}</span>
                  )}
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                  {product.shopTag && (
                    <span className="px-1.5 py-0.5 bg-red-100 text-red-600 rounded">
                      {product.shopTag}
                    </span>
                  )}
                  <span>{product.shopName}</span>
                </div>
              </div>

              {/* Select Button */}
              <div className="flex items-center">
                <Button
                  size="sm"
                  variant={selectedId === product.id ? 'primary' : 'outline'}
                  disabled={selectedId === product.id}
                >
                  {selectedId === product.id ? '已选择' : '选择'}
                </Button>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
