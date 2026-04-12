import { X, HelpCircle, Search, MessageSquare, BarChart3, Shield } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpModal({ isOpen, onClose }: HelpModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 弹窗内容 */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HelpCircle className="text-blue-500" size={24} />
            <h2 className="text-xl font-bold text-gray-800">使用指南</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-6">
          {/* 简介 */}
          <div className="bg-blue-50 rounded-xl p-4">
            <p className="text-gray-700 leading-relaxed">
              <strong className="text-blue-700">避雷真</strong> 是一款智能商品口碑分析助手，
              帮您分析淘宝评论、小红书笔记和黑猫投诉，识别虚假好评，提供购买建议。
            </p>
          </div>

          {/* 功能模块 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Search className="text-green-500" size={20} />
                <h3 className="font-semibold text-gray-800">商品搜索</h3>
              </div>
              <p className="text-sm text-gray-600">
                输入"帮我分析[品牌][商品]"即可开始分析。例如："帮我分析德芙巧克力"
              </p>
            </div>

            <div className="border border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquare className="text-pink-500" size={20} />
                <h3 className="font-semibold text-gray-800">小红书分析</h3>
              </div>
              <p className="text-sm text-gray-600">
                输入"搜索小红书[关键词]"获取笔记分析。例如："搜索小红书德芙避雷"
              </p>
            </div>

            <div className="border border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="text-orange-500" size={20} />
                <h3 className="font-semibold text-gray-800">黑猫投诉</h3>
              </div>
              <p className="text-sm text-gray-600">
                输入"搜索黑猫[品牌]"查看投诉情况。例如："搜索黑猫德芙"
              </p>
            </div>

            <div className="border border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="text-blue-500" size={20} />
                <h3 className="font-semibold text-gray-800">情感分析</h3>
              </div>
              <p className="text-sm text-gray-600">
                自动识别讽刺评论、虚假好评，生成购买建议和口碑总结
              </p>
            </div>
          </div>

          {/* 使用示例 */}
          <div>
            <h3 className="font-semibold text-gray-800 mb-3">常用指令示例</h3>
            <div className="space-y-2">
              <div className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                <span className="text-blue-500 font-mono text-sm">💬</span>
                <div>
                  <p className="text-gray-800 font-medium">"帮我分析雀巢咖啡"</p>
                  <p className="text-gray-500 text-sm">分析淘宝评论（默认）</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                <span className="text-pink-500 font-mono text-sm">📱</span>
                <div>
                  <p className="text-gray-800 font-medium">"搜索小红书 iPhone15 避雷"</p>
                  <p className="text-gray-500 text-sm">分析小红书避坑笔记</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                <span className="text-orange-500 font-mono text-sm">⚠️</span>
                <div>
                  <p className="text-gray-800 font-medium">"搜索黑猫投诉 三只松鼠"</p>
                  <p className="text-gray-500 text-sm">查询品牌投诉记录</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                <span className="text-green-500 font-mono text-sm">🔍</span>
                <div>
                  <p className="text-gray-800 font-medium">"分析德芙巧克力在淘宝、小红书、黑猫的风评"</p>
                  <p className="text-gray-500 text-sm">全平台综合分析</p>
                </div>
              </div>
            </div>
          </div>

          {/* 提示 */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <h4 className="font-semibold text-amber-800 mb-2">💡 小贴士</h4>
            <ul className="text-sm text-amber-700 space-y-1 list-disc list-inside">
              <li>支持多轮对话，可连续提问</li>
              <li>对话自动保存，可在左侧历史记录中查看</li>
              <li>点击历史记录可继续之前的对话</li>
              <li>爬虫分析可能需要一些时间，请耐心等待</li>
            </ul>
          </div>
        </div>

        {/* 底部 */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            我知道了
          </button>
        </div>
      </div>
    </div>
  );
}
