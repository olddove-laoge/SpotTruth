# 避雷真 Agent 架构说明

## 项目结构

```
new_idea/
├── __init__.py          # 包导出
├── main.py              # 程序入口
├── config.py            # 配置管理
├── models.py            # 数据模型
├── infrastructure.py    # 基础设施
├── llm_client.py        # LLM客户端
├── analyzers.py         # AI分析器
├── data_service.py      # 数据服务
├── workflows.py         # 工作流层
├── core_agent.py        # 核心Agent
└── ARCHITECTURE.md      # 本文件
```

## 架构分层

### Layer 0: Infrastructure（基础设施）
**文件**: `infrastructure.py`

- 日志系统 (logging)
- 异常定义 (AgentError, ToolError等)
- 工具装饰器 (with_retry, timed_tool, validate_required_fields)
- 事件总线 (EventBus)
- 工具结果包装 (ToolResult)

### Layer 1: Config & Models（配置与模型）
**文件**: `config.py`, `models.py`

**config.py**:
- 路径配置 (PathsConfig)
- Kimi API配置 (KimiConfig)
- 分析参数 (AnalysisConfig)
- 会话配置 (SessionConfig)

**models.py**:
- 枚举类型: SourceType, SentimentType, AnalysisStatus
- 数据类: Comment, ProductInfo, AnalysisResult等
- 会话模型: Session

### Layer 2: LLM Client（LLM客户端）
**文件**: `llm_client.py`

- LLMClient: 抽象基类
- KimiClient: Kimi API具体实现
- 功能: chat, judge_sarcasm, generate_summary, generate_advice, parse_intent

### Layer 3: Analyzers（AI分析器）
**文件**: `analyzers.py`

- CategoryClassifier: 品类分类（关键词规则）
- SarcasmDetector: 讽刺检测（TOSPrompt模型）
- SentimentAnalyzer: 情感分析（LoRA模型）
- UnifiedAnalyzer: 统一分析器（整合上述功能）

### Layer 4: Data Service（数据服务）
**文件**: `data_service.py`

- DataService: 统一数据接口
- 功能: search_product, get_comments, search_xiaohongshu, search_heimao
- 封装爬虫调用，处理异常情况

### Layer 5: Workflows（工作流）
**文件**: `workflows.py`

- Workflow: 抽象基类
- ProductAnalysisWorkflow: 完整商品分析流程
- SingleSourceWorkflow: 单一数据源搜索
- ComparisonWorkflow: 商品对比（待实现）
- WorkflowFactory: 工作流工厂

### Layer 6: Core Agent（核心Agent）
**文件**: `core_agent.py`

- BileizhenAgent: 主Agent类
- AgentBuilder: 流式构建器
- 功能: 对话管理、意图路由、结果格式化

## 数据流

```
用户输入
    │
    ▼
┌─────────────────┐
│   parse_intent  │  (LLM解析意图)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WorkflowFactory │  (创建工作流)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Workflow     │  (执行业务流程)
│    (execute)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
DataService  UnifiedAnalyzer
(采集数据)   (分析数据)
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│  AnalysisResult │  (结果数据)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ format_response │  (格式化输出)
└────────┬────────┘
         │
         ▼
    展示给用户
```

## 关键设计决策

### 1. 分层架构
- 上层依赖下层，下层不依赖上层
- 每层职责单一，便于测试和维护

### 2. 工作流模式
- 将业务流程封装为工作流
- 通过工厂模式创建工作流
- 便于扩展新的业务场景

### 3. 统一分析器
- 将讽刺检测+LLM判断+情感分析封装为一个步骤
- 避免LLM选择错误工具的问题
- 内部自动处理流程依赖

### 4. 事件驱动
- 使用EventBus进行组件间通信
- 解耦分析流程和状态管理
- 便于添加监控和日志

### 5. 配置集中化
- 所有配置集中在config.py
- 支持环境变量覆盖
- 避免硬编码

## 与原版的改进对比

| 方面 | 原版 (agent.py) | 新版 |
|------|----------------|------|
| 架构 | 扁平化，9个工具直接暴露 | 分层架构，工作流封装 |
| 工具调用 | LLM容易走错流程 | 工作流内固定流程 |
| 错误处理 | 分散，不完善 | 统一异常体系 |
| 配置管理 | 硬编码 | 集中配置，支持环境变量 |
| 可扩展性 | 差 | 工作流模式，易于扩展 |
| 测试性 | 难测试 | 分层清晰，便于单元测试 |
| 代码复用 | 低 | 组件化，高复用 |

## 使用方式

### 基础使用

```python
from new_idea import BileizhenAgent, AgentBuilder, create_driver

driver = create_driver()
agent = AgentBuilder().with_driver(driver).build()
agent.run()
```

### 自定义配置

```python
from new_idea import AgentBuilder

agent = AgentBuilder() \
    .with_driver(driver) \
    .with_profile("/path/to/profile") \
    .with_auto_save(False) \
    .build()
```

### 单独使用组件

```python
from new_idea.analyzers import UnifiedAnalyzer
from new_idea.llm_client import KimiClient

llm = KimiClient()
analyzer = UnifiedAnalyzer(llm)

results = analyzer.analyze_comments(
    comments=[...],
    product_name="德芙 巧克力",
    category="dairy"
)
```

## 扩展指南

### 添加新的工作流

```python
class CustomWorkflow(Workflow):
    def execute(self, context: WorkflowContext) -> AnalysisResult:
        # 实现业务逻辑
        pass

# 在WorkflowFactory中注册
workflows = {
    "custom": CustomWorkflow,
    # ...
}
```

### 添加新的分析器

```python
class NewAnalyzer:
    def analyze(self, text: str) -> Result:
        pass

# 在UnifiedAnalyzer中集成
```

## 待办事项

- [ ] 实现 ComparisonWorkflow（商品对比）
- [ ] 添加更多单元测试
- [ ] 优化爬虫模块，避免临时文件
- [ ] 添加缓存机制
- [ ] 实现知识库RAG功能
