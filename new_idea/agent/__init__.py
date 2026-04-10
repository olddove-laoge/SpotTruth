"""Agent模块 - 避雷真核心组件

包含:
- core_agent: 主Agent类和构建器
- models: 数据模型
- infrastructure: 基础设施
- llm_client: LLM客户端
- analyzers: AI分析器
- data_service: 数据服务
- workflows: 工作流
"""

import sys
import os

# 确保父目录在路径中（支持直接运行和作为包导入）
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# 使用绝对导入
from agent.core_agent import BileizhenAgent, AgentBuilder, create_driver
from agent.models import (
    AnalysisResult, Comment, ProductInfo,
    SentimentResult, SentimentType, AnalysisStatus,
)
from agent.infrastructure import (
    logger, events, ToolResult, ToolError,
    with_retry, timed_tool
)
from agent.llm_client import LLMClient, KimiClient
from agent.analyzers import (
    UnifiedAnalyzer, CategoryClassifier,
    SarcasmDetector, SentimentAnalyzer
)
from agent.data_service import DataService, CrawlerConfig
from agent.gateway_client import (
    GatewayClient, GatewayConfig, GatewayDataService,
    GatewayError, create_gateway_client, test_gateway_connection
)
from agent.workflows import (
    Workflow, ProductAnalysisWorkflow,
    SingleSourceWorkflow, WorkflowFactory, WorkflowContext
)

__all__ = [
    "BileizhenAgent", "AgentBuilder", "create_driver",
    "AnalysisResult", "Comment", "ProductInfo",
    "SentimentResult", "SentimentType", "AnalysisStatus",
    "logger", "events", "ToolResult",
    "ToolError", "with_retry", "timed_tool",
    "LLMClient", "KimiClient", "UnifiedAnalyzer",
    "CategoryClassifier", "SarcasmDetector", "SentimentAnalyzer",
    "DataService", "CrawlerConfig", "Workflow",
    "ProductAnalysisWorkflow", "SingleSourceWorkflow", "WorkflowFactory",
    "WorkflowContext",
    "GatewayClient", "GatewayConfig", "GatewayDataService",
    "GatewayError", "create_gateway_client", "test_gateway_connection",
]
