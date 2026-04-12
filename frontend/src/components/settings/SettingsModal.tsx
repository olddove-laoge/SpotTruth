import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, RotateCcw, Check, AlertCircle, Globe, Key, Folder } from 'lucide-react';
import { Button } from '../ui/Button';
import { useSettingsStore, DEFAULT_DRIVER_PATH, DEFAULT_KIMI_API_KEY } from '../../store/settingsStore';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const {
    driverPath,
    kimiApiKey,
    browserLoggedIn,
    setDriverPath,
    setKimiApiKey,
    loginBrowser,
    loadSettings,
    resetToDefaults,
  } = useSettingsStore();

  const [localDriverPath, setLocalDriverPath] = useState(driverPath);
  const [localApiKey, setLocalApiKey] = useState(kimiApiKey);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // 加载设置
  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen, loadSettings]);

  // 同步本地状态
  useEffect(() => {
    setLocalDriverPath(driverPath);
    setLocalApiKey(kimiApiKey);
  }, [driverPath, kimiApiKey]);

  // 保存设置
  const handleSave = () => {
    setDriverPath(localDriverPath);
    setKimiApiKey(localApiKey);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  // 重置为默认值
  const handleReset = () => {
    if (confirm('确定要恢复默认设置吗？')) {
      resetToDefaults();
      setLocalDriverPath(DEFAULT_DRIVER_PATH);
      setLocalApiKey(DEFAULT_KIMI_API_KEY);
    }
  };

  // 浏览器登录
  const handleBrowserLogin = async () => {
    setIsLoggingIn(true);
    try {
      await loginBrowser();
      alert('浏览器登录完成！\n\n请在打开的浏览器中依次登录:\n1. 淘宝 (taobao.com)\n2. 小红书 (xiaohongshu.com)\n3. 黑猫投诉 (tousu.sina.com.cn)\n\n登录完成后关闭浏览器即可。');
    } catch (error) {
      alert('登录失败: ' + (error instanceof Error ? error.message : '请检查EdgeDriver路径'));
    } finally {
      setIsLoggingIn(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* 背景遮罩 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* 弹窗内容 */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
        >
          {/* 头部 */}
          <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-800">设置</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* 内容 */}
          <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {/* API 配置 */}
            <section className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <Key className="w-5 h-5 text-primary-500" />
                API 配置
              </h3>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Kimi API Key
                  </label>
                  <input
                    type="password"
                    value={localApiKey}
                    onChange={(e) => setLocalApiKey(e.target.value)}
                    placeholder="请输入 Kimi API Key"
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    用于商品分析和情感识别的大模型 API
                  </p>
                </div>
              </div>
            </section>

            {/* EdgeDriver 配置 */}
            <section className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <Folder className="w-5 h-5 text-primary-500" />
                EdgeDriver 配置
              </h3>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  EdgeDriver 路径
                </label>
                <input
                  type="text"
                  value={localDriverPath}
                  onChange={(e) => setLocalDriverPath(e.target.value)}
                  placeholder="请输入 msedgedriver.exe 的完整路径"
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all font-mono text-sm"
                />
                <p className="mt-1 text-xs text-gray-500">
                  用于控制浏览器自动化爬取数据
                </p>
              </div>
            </section>

            {/* 浏览器登录 */}
            <section className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary-500" />
                浏览器登录
              </h3>
              <p className="text-sm text-gray-600">
                打开浏览器并依次登录淘宝、小红书、黑猫投诉。使用统一的浏览器 Profile，登录状态会自动保存。
              </p>

              <div className="p-4 border border-gray-200 rounded-xl hover:border-primary-300 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Globe className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-800">统一浏览器登录</h4>
                      <p className="text-xs text-gray-500">
                        {browserLoggedIn ? '已完成登录' : '未登录'}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant={browserLoggedIn ? 'outline' : 'primary'}
                    onClick={handleBrowserLogin}
                    disabled={isLoggingIn}
                    className={browserLoggedIn ? '' : 'shadow-sm'}
                  >
                    {isLoggingIn ? (
                      <span className="flex items-center gap-1">
                        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        启动中...
                      </span>
                    ) : browserLoggedIn ? (
                      <span className="flex items-center gap-1">
                        <Check className="w-4 h-4" />
                        重新登录
                      </span>
                    ) : (
                      '开始登录'
                    )}
                  </Button>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-xs text-gray-500 mb-2">登录步骤：</p>
                  <ol className="text-xs text-gray-600 space-y-1 list-decimal list-inside">
                    <li>点击"开始登录"打开 Edge 浏览器</li>
                    <li>访问淘宝并登录 (taobao.com)</li>
                    <li>访问小红书并登录 (xiaohongshu.com)</li>
                    <li>访问黑猫投诉并登录 (tousu.sina.com.cn)</li>
                    <li>关闭浏览器，完成</li>
                  </ol>
                </div>
              </div>
            </section>

            {/* 提示 */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-medium mb-1">说明</p>
                <ul className="space-y-1 list-disc list-inside">
                  <li>修改配置后请点击保存按钮</li>
                  <li>浏览器登录会打开 Edge 窗口，请手动完成三个平台的登录</li>
                  <li>登录状态保存在 C:\unified_bot_profile，下次自动生效</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 底部按钮 */}
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-between">
            <Button
              variant="ghost"
              onClick={handleReset}
              className="text-gray-600"
            >
              <RotateCcw className="w-4 h-4 mr-1.5" />
              恢复默认
            </Button>
            <div className="flex gap-3">
              <Button variant="outline" onClick={onClose}>
                取消
              </Button>
              <Button
                onClick={handleSave}
                className={saveSuccess ? 'bg-green-500 hover:bg-green-600' : ''}
              >
                {saveSuccess ? (
                  <span className="flex items-center gap-1.5">
                    <Check className="w-4 h-4" />
                    已保存
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5">
                    <Save className="w-4 h-4" />
                    保存
                  </span>
                )}
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
