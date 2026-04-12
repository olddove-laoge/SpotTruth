import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // 网关 API 代理（统一走网关）
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // 如果请求没有 Authorization 头，添加一个测试用的
            if (!req.headers['authorization']) {
              // 这里应该使用从登录接口获取的 token
              // 临时方案：添加一个测试 token（需要你先登录获取）
              console.log('Adding auth header for:', req.url)
            }
          })
        },
      },
      // 爬虫 API 代理（统一走网关）
      '/crawler': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/readyz': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
