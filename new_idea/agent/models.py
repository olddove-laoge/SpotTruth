"""数据模型定义"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Literal
from enum import Enum, auto
from datetime import datetime


class SourceType(Enum):
    """数据来源"""
    TAOBAO = "taobao"
    XIAOHONGSHU = "xiaohongshu"
    HEIMAO = "heimao"


class SentimentType(Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class AnalysisStatus(Enum):
    """分析状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Comment:
    """评论数据"""
    text: str
    source: SourceType
    author: str = ""
    time: str = ""
    rating: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "source": self.source.value,
            "author": self.author,
            "time": self.time,
            "rating": self.rating,
            "metadata": self.metadata
        }


@dataclass
class ProductInfo:
    """商品信息"""
    name: str
    url: str
    price: str = ""
    sales: str = ""
    shop_name: str = ""
    shop_tag: str = ""
    image_url: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SarcasmResult:
    """讽刺检测结果"""
    text: str
    is_sarcasm: bool
    confidence: float
    topic: str = ""

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "is_sarcasm": self.is_sarcasm,
            "confidence": self.confidence,
            "topic": self.topic
        }


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    sentiment: SentimentType
    confidence: float
    is_sarcasm: bool = False
    sarcasm_confidence: float = 0.0
    llm_analysis: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "sentiment": self.sentiment.value,
            "confidence": self.confidence,
            "is_sarcasm": self.is_sarcasm,
            "sarcasm_confidence": self.sarcasm_confidence,
            "llm_analysis": self.llm_analysis
        }


@dataclass
class SentimentStatistics:
    """情感统计结果"""
    total: int = 0
    positive_count: int = 0
    negative_count: int = 0
    sarcasm_count: int = 0
    positive_rate: float = 0.0
    negative_rate: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AnalysisResult:
    """完整分析结果"""
    product_name: str
    brand: str = ""
    category: str = ""
    status: AnalysisStatus = AnalysisStatus.PENDING

    # 原始数据
    product_info: Optional[ProductInfo] = None
    taobao_comments: List[Comment] = field(default_factory=list)
    xiaohongshu_notes: List[Comment] = field(default_factory=list)
    heimao_complaints: List[Comment] = field(default_factory=list)

    # 分析结果
    sentiment_results: List[SentimentResult] = field(default_factory=list)
    statistics: Optional[SentimentStatistics] = None

    # 报告
    summary: str = ""
    advice: str = ""
    key_issues: List[str] = field(default_factory=list)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)

    # 平台分析记录（用于对比功能）
    analyzed_platforms: List[str] = field(default_factory=list)  # ["taobao", "xiaohongshu", "heimao"]
    has_taobao: bool = False
    has_xiaohongshu: bool = False
    has_heimao: bool = False

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_platforms_summary(self) -> str:
        """获取已分析平台的摘要"""
        platforms = []
        if self.has_taobao:
            platforms.append(f"淘宝({len(self.taobao_comments)}条)")
        if self.has_xiaohongshu:
            platforms.append(f"小红书({len(self.xiaohongshu_notes)}条)")
        if self.has_heimao:
            platforms.append(f"黑猫({len(self.heimao_complaints)}条)")
        return " + ".join(platforms) if platforms else "无数据"

    def to_dict(self) -> Dict:
        return {
            "product_name": self.product_name,
            "brand": self.brand,
            "category": self.category,
            "status": self.status.value,
            "product_info": self.product_info.to_dict() if self.product_info else None,
            "taobao_comments": [c.to_dict() for c in self.taobao_comments],
            "xiaohongshu_notes": [c.to_dict() for c in self.xiaohongshu_notes],
            "heimao_complaints": [c.to_dict() for c in self.heimao_complaints],
            "sentiment_results": [r.to_dict() for r in self.sentiment_results],
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "summary": self.summary,
            "advice": self.advice,
            "key_issues": self.key_issues,
            "pros": self.pros,
            "cons": self.cons,
            "analyzed_platforms": self.analyzed_platforms,
            "has_taobao": self.has_taobao,
            "has_xiaohongshu": self.has_xiaohongshu,
            "has_heimao": self.has_heimao,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class UserIntent:
    """用户意图解析结果"""
    action: Literal["analyze", "compare", "search_xhs", "search_heimao", "help", "unknown"]
    brand: str = ""
    product: str = ""
    products: List[tuple] = field(default_factory=list)  # [(brand, product), ...]
    need_xiaohongshu: bool = False
    need_heimao: bool = False
    raw_input: str = ""


@dataclass
class Session:
    """会话状态"""
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    current_analysis: Optional[AnalysisResult] = None
    analysis_history: List[AnalysisResult] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    def add_to_history(self, role: str, content: str):
        """添加对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # 限制历史长度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def save_analysis(self, analysis: AnalysisResult):
        """保存分析结果到历史"""
        self.analysis_history.append(analysis)
        self.current_analysis = analysis

    def get_last_analyzed_platforms(self) -> List[str]:
        """获取上次分析的平台列表"""
        if self.current_analysis:
            return self.current_analysis.analyzed_platforms
        return []

    def get_current_product_info(self) -> Optional[Dict]:
        """获取当前商品信息"""
        if not self.current_analysis:
            return None
        return {
            "product_name": self.current_analysis.product_name,
            "brand": self.current_analysis.brand,
            "category": self.current_analysis.category,
            "platforms": self.current_analysis.analyzed_platforms,
            "has_taobao": self.current_analysis.has_taobao,
            "has_xiaohongshu": self.current_analysis.has_xiaohongshu,
            "has_heimao": self.current_analysis.has_heimao
        }
