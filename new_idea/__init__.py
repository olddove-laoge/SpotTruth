"""避雷真 - 商品口碑分析Agent

重构后的架构：
- agent/: 核心Agent模块
  - core_agent.py: 主Agent类和构建器
  - models.py: 数据模型
  - infrastructure.py: 基础设施
  - llm_client.py: LLM客户端
  - analyzers.py: AI分析器
  - data_service.py: 数据服务
  - workflows.py: 工作流
- config.py: 全局配置
- main.py: 程序入口
- run.py: 启动脚本

使用示例:
    from new_idea import BileizhenAgent, AgentBuilder, create_driver
    from new_idea.config import paths, kimi

    driver = create_driver()
    agent = AgentBuilder().with_driver(driver).build()
    agent.run()
"""

# 从agent模块导出核心类
from .agent import (
    BileizhenAgent,
    AgentBuilder,
    create_driver,
    AnalysisResult,
    Comment,
    ProductInfo,
    SentimentResult,
    SentimentType,
    AnalysisStatus,
    logger,
    KimiClient,
    UnifiedAnalyzer,
    DataService,
)

# 从config导出配置
from .config import paths, kimi, analysis, session, CATEGORIES

__all__ = [
    # Agent核心
    "BileizhenAgent",
    "AgentBuilder",
    "create_driver",
    # 数据模型
    "AnalysisResult",
    "Comment",
    "ProductInfo",
    "SentimentResult",
    "SentimentType",
    "AnalysisStatus",
    # 工具
    "logger",
    "KimiClient",
    "UnifiedAnalyzer",
    "DataService",
    # 配置
    "paths",
    "kimi",
    "analysis",
    "session",
    "CATEGORIES",
]

__version__ = "2.0.0"
