"""配置管理 - 集中管理所有配置项"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass(frozen=True)
class PathsConfig:
    """路径配置"""
    driver_path: str = r"E:\edgedriver_win64 (1)\msedgedriver.exe"
    profile_dir: str = r"C:\unified_bot_profile"
    cache_dir: str = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"

    # 项目内部路径
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data")
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent / "output")
    lora_dir: Path = field(default_factory=lambda: Path(__file__).parent / "output" / "lora")
    sarcasm_dir: Path = field(default_factory=lambda: Path(__file__).parent / "sarcasm_detection" / "output_prompt")
    kb_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data" / "knowledge_base")

    # 外部爬虫路径
    taobao_crawler_path: str = r"D:\C_data\SpotTruth\AIGC\Comment_crawling_and_analysis"
    xhs_crawler_path: str = r"D:\C_data\SpotTruth\AIGC\Comparison_of_similar_products_and_external_link_information"

    def __post_init__(self):
        # 确保目录存在
        for dir_path in [self.data_dir, self.output_dir, self.kb_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class KimiConfig:
    """Kimi API配置"""
    # 方式1：从环境变量读取（推荐）
    # api_key: str = field(default_factory=lambda: os.getenv("KIMI_API_KEY", ""))

    # 方式2：直接填写（仅测试用，不要提交到git）
    api_key: str = "sk-NxnJvWVKw9cun9Y80gjfQp7PyWR9rOMwy9VH2aNU28xOdxcr"
    base_url: str = "https://api.moonshot.cn/v1"
    model: str = "moonshot-v1-8k"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60


@dataclass(frozen=True)
class AnalysisConfig:
    """分析参数配置"""
    sarcasm_threshold: float = 0.6
    confidence_threshold: float = 0.6
    max_comments: int = 100
    max_xhs_notes: int = 30
    max_heimao_complaints: int = 50
    max_retries: int = 2


@dataclass(frozen=True)
class SessionConfig:
    """会话配置"""
    max_history: int = 20  # 最大保留对话轮数
    auto_save: bool = True
    session_file: str = "session.json"


# 全局配置实例
paths = PathsConfig()
kimi = KimiConfig()
analysis = AnalysisConfig()
session = SessionConfig()


# 商品品类定义
CATEGORIES = [
    "book", "tablet", "electronics", "fruit",
    "shampoo", "dairy", "clothing", "water_heater", "hotel"
]


# 品类关键词映射
CATEGORY_KEYWORDS = {
    "book": ["书", "图书", "小说", "教材", "绘本", "书籍"],
    "tablet": ["平板", "ipad", "平板电脑", "surface"],
    "electronics": ["手机", "iphone", "安卓", "电脑", "笔记本", "电子产品"],
    "fruit": ["水果", "苹果", "橙子", "芒果", "草莓", "荔枝"],
    "shampoo": ["洗发水", "护发素", "洗头膏", "洗发液"],
    "dairy": ["牛奶", "酸奶", "奶酪", "奶粉", "乳制品"],
    "clothing": ["衣服", "T恤", "衬衫", "裙子", "裤子", "外套", "服装"],
    "water_heater": ["热水器", "电热水器", "燃气热水器"],
    "hotel": ["酒店", "民宿", "宾馆", "客栈", "公寓"],
}
