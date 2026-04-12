import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Shield, MessageSquare, Search, BarChart3 } from 'lucide-react';
import { Button } from '../ui/Button';

interface LoginProps {
  onLogin: () => void;
}

export function Login({ onLogin }: LoginProps) {
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // 检查是否已登录（调用健康检查接口，带 cookie）
  useEffect(() => {
    const checkLogin = async () => {
      // 如果 localStorage 中没有 token，说明已经退出登录，不要自动登录
      const hasToken = localStorage.getItem('access_token');
      if (!hasToken) {
        return;
      }

      try {
        // 尝试调用一个需要认证的接口
        const response = await fetch('/api/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include', // 携带 cookie
          body: JSON.stringify({ product_name: 'test' }),
        });
        if (response.ok) {
          onLogin();
        } else {
          // 认证失败，清除 localStorage
          localStorage.removeItem('access_token');
        }
      } catch {
        // 未登录或请求失败，显示登录页
      }
    };
    checkLogin();
  }, [onLogin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          account,
          password,
          login_type: 'password',
        }),
      });

      const data = await response.json();

      if (data.code === 'OK') {
        // cookie 已由后端自动设置，同时保存到 localStorage 用于判断登录状态
        localStorage.setItem('access_token', data.data.access_token);
        onLogin();
      } else {
        setError(data.message || '登录失败');
      }
    } catch (err) {
      setError('网络错误，请检查服务是否启动');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* 左侧 - 品牌介绍 */}
      <div className="flex-1 flex flex-col justify-center items-center p-12 bg-gradient-to-br from-gray-50 to-gray-100">
        {/* Logo 动画 */}
        <motion.div
          initial={{ opacity: 0, x: -100 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mb-8"
        >
          <img
            src="/logo.svg"
            alt="避雷真"
            className="w-48 h-48 object-contain drop-shadow-lg"
          />
        </motion.div>

        {/* 标题动画 */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: 'easeOut' }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            避雷真
            <span className="text-sm font-normal text-primary-500 ml-2 px-2 py-1 bg-primary-50 rounded-full">
              Beta
            </span>
          </h1>
          <p className="text-xl text-gray-600">智能商品口碑分析助手</p>
        </motion.div>

        {/* 功能介绍 */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5, ease: 'easeOut' }}
          className="grid grid-cols-2 gap-6 max-w-lg"
        >
          <div className="flex items-start gap-3 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="p-2 bg-primary-50 rounded-lg">
              <Search className="w-5 h-5 text-primary-500" />
            </div>
            <div>
              <h3 className="font-medium text-gray-800">多平台搜索</h3>
              <p className="text-sm text-gray-500">淘宝、小红书、黑猫投诉</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="p-2 bg-green-50 rounded-lg">
              <MessageSquare className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="font-medium text-gray-800">情感分析</h3>
              <p className="text-sm text-gray-500">识别真实评价与虚假好评</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="p-2 bg-amber-50 rounded-lg">
              <Shield className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <h3 className="font-medium text-gray-800">风险预警</h3>
              <p className="text-sm text-gray-500">识别讽刺评论和投诉信息</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="p-2 bg-blue-50 rounded-lg">
              <BarChart3 className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="font-medium text-gray-800">智能对比</h3>
              <p className="text-sm text-gray-500">多商品对比分析报告</p>
            </div>
          </div>
        </motion.div>

        {/* 底部标语 */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="mt-12 text-gray-400 text-sm"
        >
          基于大语言模型 · 深度学习情感分析 · 实时数据爬取
        </motion.p>
      </div>

      {/* 右侧 - 登录表单 */}
      <div className="w-[480px] flex flex-col justify-center items-center p-12 bg-white shadow-xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-sm"
        >
          <h2 className="text-2xl font-bold text-gray-800 mb-2">欢迎登录</h2>
          <p className="text-gray-500 mb-8">请输入账号密码以继续使用</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                账号
              </label>
              <input
                type="text"
                value={account}
                onChange={(e) => setAccount(e.target.value)}
                placeholder="请输入账号"
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                disabled={isLoading}
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm"
              >
                {error}
              </motion.div>
            )}

            <Button
              type="submit"
              className="w-full py-3 text-base"
              disabled={isLoading || !account || !password}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  登录中...
                </span>
              ) : (
                '登录'
              )}
            </Button>
          </form>

          <div className="mt-8 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-400 text-center">
              默认账号: spottruth_user / spottruth_user_123
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
