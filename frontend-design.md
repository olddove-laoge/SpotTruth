# 避雷真 - 对话式商品避雷Agent前端设计方案

## 一、项目概述

基于 `run_gateway.py` 逻辑，构建一个美观简约的对话式前端界面，支持自然语言交互、商品分析、多平台数据对比等功能。

## 二、接口设计

### 2.1 基础接口

#### 健康检查
```http
GET /healthz
```
**响应:**
```json
{
  "status": "ok",
  "service": "agent-api",
  "version": "2.0.0"
}
```

#### 就绪检查
```http
GET /readyz
```
**响应:**
```json
{
  "status": "ready",
  "message": "Agent API 服务已就绪"
}
```

---

### 2.2 核心业务流程接口

#### 1. 意图解析（入口）
```http
POST /api/parse_intent
```
**请求体:**
```json
{
  "user_input": "帮我分析一下德芙巧克力怎么样",
  "conversation_history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "您好！我是避雷真..."}
  ],
  "current_product": "",
  "analyzed_platforms": []
}
```

**响应:**
```json
{
  "intent": "analyze",
  "brand": "德芙",
  "product": "巧克力",
  "need_xiaohongshu": false,
  "need_heimao": false,
  "need_taobao": true,
  "clarification_needed": false,
  "clarification_question": "",
  "response": "好的，我来帮您分析德芙巧克力 的口碑情况。"
}
```

**意图类型:**
- `analyze` - 分析商品
- `compare` - 对比商品
- `search_xhs` - 搜索小红书
- `search_heimao` - 搜索黑猫投诉
- `help` - 帮助
- `unknown` - 未知意图
- `clarification_needed` - 需要澄清

---

#### 2. 品类分类
```http
POST /api/classify
```
**请求体:**
```json
{
  "product_name": "德芙巧克力"
}
```

**响应:**
```json
{
  "product_name": "德芙巧克力",
  "category": "dairy",
  "keywords_match": true
}
```

---

#### 3. 评论分析（核心）
```http
POST /api/analyze
```
**请求体:**
```json
{
  "comments": ["评论1", "评论2", "评论3"],
  "product_name": "德芙巧克力",
  "category": "dairy"
}
```

**响应:**
```json
{
  "product_name": "德芙巧克力",
  "category": "dairy",
  "statistics": {
    "total": 100,
    "positive_count": 80,
    "negative_count": 20,
    "sarcasm_count": 5,
    "positive_rate": 0.8,
    "negative_rate": 0.2
  },
  "results": [
    {
      "text": "评论内容",
      "sentiment": "positive",
      "is_sarcasm": false,
      "confidence": 0.95,
      "sarcasm_confidence": 0,
      "llm_analysis": null
    },
    {
      "text": "呵呵，真是太好了呢",
      "sentiment": "negative",
      "is_sarcasm": true,
      "confidence": 0.92,
      "sarcasm_confidence": 0.85,
      "llm_analysis": "表面说'好'，实际表达不满"
    }
  ]
}
```

---

#### 4. 生成总结报告
```http
POST /api/summarize
```
**请求体:**
```json
{
  "statistics": {
    "total": 100,
    "positive_rate": 0.8,
    "negative_rate": 0.2,
    "sarcasm_count": 5
  },
  "sample_comments": [
    {"text": "评论", "sentiment": "positive", "is_sarcasm": false}
  ]
}
```

**响应:**
```json
{
  "summary": "该商品整体口碑较好，好评率80%。但存在5条疑似虚假好评（讽刺评论），主要问题集中在...",
  "advice": "建议购买，但需注意..."
}
```

---

#### 5. 小红书分析
```http
POST /api/analyze_xiaohongshu
```
**请求体:**
```json
{
  "notes": [
    {"title": "标题", "content": "内容...", "likes": 100}
  ],
  "keyword": "德芙巧克力"
}
```

**响应:**
```json
{
  "summary": "小红书用户主要反馈该商品口感不错，但价格偏高...",
  "key_points": ["价格偏贵", "口感丝滑", "包装精美"],
  "sentiment": "mostly_positive"
}
```

---

#### 6. 黑猫投诉分析
```http
POST /api/analyze_heimao
```
**请求体:**
```json
{
  "complaints": [
    {"title": "投诉标题", "content": "内容...", "status": "处理中"}
  ],
  "brand": "德芙"
}
```

**响应:**
```json
{
  "summary": "主要投诉类型为质量问题和物流配送...",
  "complaint_types": ["质量问题", "物流配送"],
  "severity": "medium",
  "recommendation": "建议谨慎购买，注意检查生产日期"
}
```

---

#### 7. 生成对比结论
```http
POST /api/compare_conclusion
```
**请求体:**
```json
{
  "product_a_name": "德芙巧克力",
  "product_b_name": "费列罗巧克力",
  "stats_a": {"total": 100, "positive_rate": 0.8},
  "stats_b": {"total": 120, "positive_rate": 0.9},
  "summary_a": "德芙分析总结...",
  "summary_b": "费列罗分析总结...",
  "advice_a": "建议购买...",
  "advice_b": "强烈推荐...",
  "heimao_analysis_a": {...},
  "heimao_analysis_b": {...},
  "xhs_analysis_a": {...},
  "xhs_analysis_b": {...},
  "has_taobao_a": true,
  "has_taobao_b": true
}
```

**响应:**
```json
{
  "conclusion": "综合对比，费列罗在好评率和用户满意度上略胜一筹..."
}
```

---

### 2.3 爬虫相关接口（本地服务）

> 这些接口由本地 Python 服务提供，非网关转发

#### 搜索淘宝商品
```http
POST /crawler/taobao/search
```
**请求体:**
```json
{
  "brand": "德芙",
  "product": "巧克力",
  "max_results": 5
}
```

**响应:**
```json
{
  "success": true,
  "data": [
    {
      "name": "德芙巧克力礼盒装",
      "price": "89.9",
      "sales": "月销1万+",
      "shop_name": "德芙官方旗舰店",
      "shop_tag": "天猫",
      "url": "https://...",
      "image_url": "https://..."
    }
  ]
}
```

---

#### 获取淘宝评论
```http
POST /crawler/taobao/comments
```
**请求体:**
```json
{
  "url": "https://detail.tmall.com/...",
  "brand": "德芙",
  "product": "巧克力",
  "max_count": 50
}
```

---

#### 搜索小红书
```http
POST /crawler/xiaohongshu/search
```
**请求体:**
```json
{
  "keyword": "德芙巧克力",
  "max_notes": 5
}
```

---

#### 搜索黑猫投诉
```http
POST /crawler/heimao/search
```
**请求体:**
```json
{
  "brand": "德芙",
  "max_complaints": 30
}
```

---

## 三、前端构建思路

### 3.1 技术栈选择

```
框架: React 18 + TypeScript
状态管理: Zustand (轻量级，适合对话状态)
样式: Tailwind CSS + shadcn/ui
图表: Recharts (数据可视化)
动画: Framer Motion (流畅的交互动画)
HTTP: Axios + React Query
图标: Lucide React
```

### 3.2 页面布局结构

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar (200px)              │  Main Content               │
│  ───────────────────────────  │  ─────────────────────────  │
│  🏠 首页                       │                             │
│  💬 新对话                     │   [Chat Messages Area]      │
│  ───────────────────────────  │                             │
│  📜 历史会话                   │   ┌─────────────────────┐   │
│  ├── 德芙巧克力分析             │   │  User: xxx          │   │
│  ├── iPhone 15对比             │   │  Bot: xxx           │   │
│  └── ...                       │   │  [Analysis Card]    │   │
│  ───────────────────────────  │   └─────────────────────┘   │
│                               │                             │
│  ⚙️ 设置                       │                             │
└───────────────────────────────┴─────────────────────────────┘
                              │  [Input Area - Fixed Bottom]  │
                              └───────────────────────────────┘
```

### 3.3 核心组件设计

#### 1. 对话消息组件

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type: 'text' | 'product_select' | 'analysis_report' | 'comparison_report' | 'loading';
  metadata?: {
    products?: Product[];           // 商品选择列表
    analysisResult?: AnalysisResult; // 分析结果
    comparisonResult?: ComparisonResult; // 对比结果
  };
  timestamp: number;
}
```

#### 2. 分析结果卡片

```typescript
interface AnalysisResult {
  productName: string;
  category: string;
  statistics: {
    total: number;
    positiveRate: number;
    negativeRate: number;
    sarcasmCount: number;
  };
  summary: string;
  advice: string;
  comments: CommentItem[];
  xiaohongshu?: XiaohongshuAnalysis;
  heimao?: HeimaoAnalysis;
}
```

#### 3. 商品选择卡片

展示淘宝搜索结果，供用户选择具体商品：
- 商品图片
- 名称、价格
- 销量、店铺信息
- 选择按钮

---

### 3.4 交互流程设计

#### 流程 1: 商品分析

```
1. 用户输入: "帮我分析德芙巧克力"
   ↓
2. [显示思考中...]
   ↓
3. 调用 /api/parse_intent
   ↓
4. 显示 Assistant 回复: "好的，我来帮您分析德芙巧克力..."
   ↓
5. [显示数据采集中...]
   ↓
6. 调用爬虫 /crawler/taobao/search
   ↓
7. 显示 [商品选择卡片] - 用户选择
   ↓
8. [显示爬取评论中...]
   ↓
9. 调用 /crawler/taobao/comments
   ↓
10. [显示分析中...]
    ↓
11. 并行调用:
    - /api/classify
    - /api/analyze
    - /api/summarize
    ↓
12. 显示 [分析结果卡片]
    - 统计概览（饼图/环形图）
    - 评论列表
    - 总结与建议
```

#### 流程 2: 商品对比

```
1. 用户输入: "德芙和费列罗哪个好"
   ↓
2. 解析为 compare 意图
   ↓
3. 分析商品A (带缓存检查)
   ↓
4. 分析商品B (带缓存检查)
   ↓
5. 调用 /api/compare_conclusion
   ↓
6. 显示 [对比报告卡片]
   - 并排对比表格
   - 图表对比
   - LLM 结论
```

---

### 3.5 状态管理设计

```typescript
// store/conversationStore.ts
interface ConversationState {
  // 当前会话
  sessionId: string;
  currentProduct: string;
  messages: Message[];
  conversationHistory: {role: string; content: string}[];
  
  // 加载状态
  isLoading: boolean;
  loadingText: string;
  
  // 缓存
  productCache: Map<string, ProductCache>;
  
  // Actions
  sendMessage: (text: string) => Promise<void>;
  selectProduct: (product: Product) => Promise<void>;
  clearConversation: () => void;
  loadSession: (sessionId: string) => void;
}
```

---

### 3.6 UI 设计规范

#### 配色方案
```
主色: #6366f1 (Indigo-500) - 代表信任、科技
辅色: #10b981 (Emerald-500) - 正面/好评
警示: #f59e0b (Amber-500) - 中性/警告
负面: #ef4444 (Red-500) - 负面/差评
背景: #fafafa (Gray-50) - 浅灰背景
卡片: #ffffff - 纯白卡片
```

#### 字体
```
标题: Inter, system-ui
正文: Inter, -apple-system, sans-serif
数据: SF Mono, monospace
```

#### 圆角与阴影
```
卡片圆角: rounded-xl (12px)
按钮圆角: rounded-lg (8px)
卡片阴影: shadow-sm hover:shadow-md transition
```

---

### 3.7 关键 UI 组件设计

#### 1. 分析结果卡片

```
┌─────────────────────────────────────────┐
│  📦 德芙巧克力 (dairy)                   │
├─────────────────────────────────────────┤
│                                         │
│   ┌─────────┐  ┌─────────┐  ┌────────┐ │
│   │  100   │  │  80%   │  │   5    │ │
│   │  评论  │  │ 好评率 │  │ 虚假  │ │
│   └─────────┘  └─────────┘  └────────┘ │
│                                         │
│  [情感分布饼图]                          │
│                                         │
│  📋 分析总结                             │
│  该商品整体口碑较好...                   │
│                                         │
│  💡 购买建议                             │
│  建议购买，但需注意...                   │
│                                         │
│  📝 典型评论 (3条)                       │
│  ┌─────────────────────────────────┐   │
│  │ 👍 这个巧克力真的很好吃！        │   │
│  │ 🎭 呵呵，真是太棒了呢 (讽刺)     │   │
│  └─────────────────────────────────┘   │
│                                         │
│  📱 小红书口碑:  mostly_positive        │
│  ⚠️ 黑猫投诉:   风险等级中              │
│                                         │
└─────────────────────────────────────────┘
```

#### 2. 商品对比卡片

```
┌─────────────────────────────────────────────────────────────┐
│  📊 对比报告: 德芙巧克力 vs 费列罗巧克力                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┬──────────────────┐                   │
│  │   德芙巧克力      │   费列罗巧克力    │                   │
│  ├──────────────────┼──────────────────┤                   │
│  │  评论: 100       │  评论: 120       │                   │
│  │  好评: 80%       │  好评: 90%       │                   │
│  │  虚假: 5条       │  虚假: 2条       │                   │
│  │  投诉: 10条      │  投诉: 5条       │                   │
│  └──────────────────┴──────────────────┘                   │
│                                                             │
│  [柱状图对比好评率/差评率]                                    │
│                                                             │
│  🔍 对比结论                                                 │
│  综合对比，费列罗在好评率和用户满意度上略胜一筹...            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. 商品选择卡片

```
┌─────────────────────────────────────────┐
│  📦 找到 3 个商品，请选择要分析的:       │
├─────────────────────────────────────────┤
│                                         │
│  ┌────┬─────────────────────────────┐  │
│  │ 🖼️ │ 德芙巧克力礼盒装 588g        │  │
│  │    │ 💰 ¥89.9  📈 月销1万+        │  │
│  │    │ 🏪 [天猫] 德芙官方旗舰店     │  │
│  │    │ [选择此商品]                 │  │
│  └────┴─────────────────────────────┘  │
│                                         │
│  ┌────┬─────────────────────────────┐  │
│  │ 🖼️ │ 德芙丝滑牛奶巧克力 252g     │  │
│  │    │ 💰 ¥35.8  📈 月销5000+      │  │
│  │    │ 🏪 [淘宝] 某某零食店         │  │
│  │    │ [选择此商品]                 │  │
│  └────┴─────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

---

### 3.8 响应式设计

```
Desktop (>= 1024px):
  - Sidebar 展开显示
  - 双列对比布局
  
Tablet (768px - 1023px):
  - Sidebar 可折叠
  - 单列布局，对比改为上下排列
  
Mobile (< 768px):
  - Sidebar 隐藏为抽屉
  - 全屏消息区域
  - 底部固定输入框
```

---

## 四、项目目录结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── ui/                 # shadcn/ui 基础组件
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── TypingIndicator.tsx
│   │   ├── analysis/
│   │   │   ├── AnalysisCard.tsx
│   │   │   ├── SentimentChart.tsx
│   │   │   ├── CommentList.tsx
│   │   │   └── SummarySection.tsx
│   │   ├── compare/
│   │   │   ├── ComparisonCard.tsx
│   │   │   ├── ComparisonTable.tsx
│   │   │   └── ComparisonChart.tsx
│   │   ├── product/
│   │   │   ├── ProductSelectCard.tsx
│   │   │   └── ProductItem.tsx
│   │   └── layout/
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── LoadingOverlay.tsx
│   ├── hooks/
│   │   ├── useConversation.ts
│   │   ├── useAnalysis.ts
│   │   └── useCrawler.ts
│   ├── store/
│   │   └── conversationStore.ts
│   ├── services/
│   │   ├── api.ts              # 网关 API
│   │   └── crawler.ts          # 爬虫 API
│   ├── types/
│   │   ├── message.ts
│   │   ├── analysis.ts
│   │   └── product.ts
│   ├── utils/
│   │   └── formatters.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 五、实现优先级

### Phase 1: 基础对话 (MVP)
- [ ] 项目初始化 + 基础布局
- [ ] 对话消息组件
- [ ] 意图解析接口对接
- [ ] 文本类型消息流转

### Phase 2: 商品分析
- [ ] 商品选择卡片
- [ ] 爬虫接口对接
- [ ] 分析结果展示卡片
- [ ] 情感分布图表

### Phase 3: 多平台支持
- [ ] 小红书分析展示
- [ ] 黑猫投诉展示
- [ ] 多平台数据整合视图

### Phase 4: 对比功能
- [ ] 商品对比流程
- [ ] 对比表格/图表
- [ ] 对比结论展示

### Phase 5: 优化增强
- [ ] 会话历史管理
- [ ] 响应式适配
- [ ] 动画优化
- [ ] 错误处理与重试

---

## 六、与后端的联调要点

1. **开发环境代理配置**: Vite 配置代理到本地网关 (:8080)
2. **爬虫服务**: 需要同时启动 Python 爬虫服务 (:5000 或其他端口)
3. **CORS 配置**: 确保网关允许前端跨域访问
4. **超时处理**: 爬虫接口可能较慢，需要 loading 状态和超时提示
5. **错误处理**: 网关熔断、限流时的降级提示
