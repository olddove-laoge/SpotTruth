# 避雷真 - 对话式商品避雷 Agent 前端

基于 React + TypeScript + Tailwind CSS 构建的对话式商品口碑分析前端界面。

## 功能特性

- 💬 **对话式交互** - 自然语言输入，LLM 意图解析
- 📦 **商品分析** - 淘宝评论情感分析 + 讽刺检测
- 📱 **多平台数据** - 小红书笔记、黑猫投诉整合
- 📊 **可视化报告** - 图表展示分析结果
- 🔄 **商品对比** - 多商品对比分析
- 💾 **会话管理** - 历史会话保存与恢复

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **图表**: Recharts
- **动画**: Framer Motion
- **图标**: Lucide React

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件（如果使用本地开发代理，通常不需要修改）

### 3. 启动开发服务器

```bash
npm run dev
```

前端服务将运行在 http://localhost:3000

### 4. 联调后端服务

确保以下服务已启动：

**终端 A - Agent API 服务:**
```bash
cd ../new_idea
python agent_api.py
```

**终端 B - Go 网关:**
```bash
cd ../go_backend
go run ./cmd/api-gateway
```

**终端 C - 爬虫服务（如果需要）:**
```bash
cd ../new_idea
python crawler_service.py  # 如果有独立的爬虫服务
```

## 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # 基础 UI 组件 (Button, Card, Input)
│   │   ├── chat/         # 聊天相关组件
│   │   ├── analysis/     # 分析结果展示组件
│   │   ├── product/      # 商品选择组件
│   │   ├── compare/      # 对比功能组件
│   │   └── layout/       # 布局组件 (Sidebar)
│   ├── services/
│   │   ├── api.ts        # 网关 API 封装
│   │   └── crawler.ts    # 爬虫 API 封装
│   ├── store/
│   │   └── conversationStore.ts  # Zustand 状态管理
│   ├── types/
│   │   └── index.ts      # TypeScript 类型定义
│   ├── App.tsx           # 主应用组件
│   └── main.tsx          # 入口文件
├── .env.example          # 环境变量示例
└── vite.config.ts        # Vite 配置
```

## 使用指南

### 基础对话

1. 在输入框中输入消息，例如：
   - "帮我分析德芙巧克力"
   - "iPhone 15 怎么样"
   - "搜索小红书上的避雷笔记"

2. 根据提示选择商品（从搜索结果中）

3. 查看分析结果：
   - 概览：好评率、虚假好评数、情感分布
   - 评论：典型好评/差评/讽刺评论
   - 小红书：笔记分析（如果有）
   - 黑猫：投诉分析（如果有）

### 商品对比

输入："德芙巧克力和费列罗巧克力哪个好"

系统将：
1. 分别分析两个商品
2. 生成对比报告
3. 给出购买建议

## 开发说明

### 添加新功能

1. **新增 API 接口**: 在 `services/api.ts` 中添加
2. **新增组件**: 在 `components/` 下创建，遵循现有结构
3. **新增类型**: 在 `types/index.ts` 中定义

### 状态管理

使用 Zustand 管理全局状态：

```typescript
const { messages, sendMessage, isLoading } = useConversationStore()
```

### 样式规范

- 使用 Tailwind CSS 工具类
- 颜色主题：Primary (#6366f1), Success (#10b981), Warning (#f59e0b), Danger (#ef4444)
- 圆角：rounded-lg (8px), rounded-xl (12px)

## 构建部署

```bash
# 生产构建
npm run build

# 预览构建结果
npm run preview
```

构建输出在 `dist/` 目录。

## 注意事项

1. **开发环境**: Vite 代理会自动转发 API 请求到后端服务
2. **爬虫依赖**: 商品搜索功能需要本地爬虫服务
3. **浏览器兼容**: 支持现代浏览器（Chrome, Firefox, Safari, Edge）
