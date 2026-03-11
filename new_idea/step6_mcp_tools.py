# step6_mcp_tools.py
"""
Step 6: MCP工具封装 - 避雷真
- 数据采集工具（淘宝、小红书、黑猫）
- 品类分类工具
- 情感分析工具（LoRA）
- 讽刺检测工具（TOSPrompt）
- LLM判断工具（Kimi）
- 知识库工具（RAG）
- 报告生成工具

支持场景：商品分析、书评分析、酒店分析
"""

import os
import json
import time
import torch
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel
import numpy as np


# ============== 配置 ==============

CATEGORIES = ["book", "tablet", "electronics", "fruit", "shampoo", "dairy", "clothing", "water_heater", "hotel"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
LORA_DIR = os.path.join(OUTPUT_DIR, "lora")
SARCASM_DIR = os.path.join(OUTPUT_DIR, "sarcasm_detection", "output")
KNOWLEDGE_BASE_DIR = os.path.join(SCRIPT_DIR, "data", "knowledge_base")

KIMI_API_KEY = "sk-NxnJvWVKw9cun9Y80gjfQp7PyWR9rOMwy9VH2aNU28xOdxcr"
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_MODEL = "moonshot-v1-8k"

CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"


# ============== 数据结构 ==============

class TaskType(Enum):
    """任务类型"""
    PRODUCT = "product"       # 商品分析
    BOOK = "book"            # 书评分析
    HOTEL = "hotel"          # 酒店分析
    DIRECT = "direct"        # 直接分析


class SentimentType(Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"


class SceneType(Enum):
    """分析场景"""
    TAOBAO = "taobao"
    XIAOHONGSHU = "xiaohongshu"
    HEIMAO = "heimao"


@dataclass
class Comment:
    """评论数据结构"""
    text: str
    source: str
    author: str = ""
    time: str = ""
    rating: float = 0.0


@dataclass
class Product:
    """商品数据结构"""
    name: str
    brand: str
    category: str
    comments: List[Comment] = field(default_factory=list)
    source: str = ""


@dataclass
class SentimentResult:
    """情感分析结果"""
    sentiment: SentimentType
    confidence: float
    is_sarcasm: bool = False
    sarcasm_confidence: float = 0.0
    original_text: str = ""


@dataclass
class AnalysisReport:
    """分析报告"""
    keyword: str
    category: str
    total_comments: int
    positive_count: int
    negative_count: int
    sarcasm_count: int
    llm_judged: List[Dict] = field(default_factory=list)
    knowledge_base_context: str = ""
    summary: str = ""
    advice: str = ""


# ============== 知识库管理 ==============

class KnowledgeBase:
    """RAG知识库管理"""
    
    def __init__(self, base_dir: str = KNOWLEDGE_BASE_DIR):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        
        self.category_files = {}
        for cat in CATEGORIES:
            cat_dir = os.path.join(base_dir, cat)
            os.makedirs(cat_dir, exist_ok=True)
            self.category_files[cat] = os.path.join(cat_dir, "knowledge.json")
    
    def query(self, category: str, brand: str = "", product: str = "", top_k: int = 3) -> List[Dict]:
        """查询知识库"""
        category = category.lower()
        if category not in self.category_files:
            return []
        
        kb_file = self.category_files[category]
        if not os.path.exists(kb_file):
            return []
        
        with open(kb_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        search_key = f"{brand} {product}".lower()
        
        for item in data:
            if brand and brand.lower() in item.get("brand", "").lower():
                results.append(item)
            elif product and product.lower() in item.get("product", "").lower():
                results.append(item)
        
        return results[:top_k]
    
    def update(self, category: str, brand: str, product: str, summary: str, advice: str = ""):
        """更新知识库"""
        category = category.lower()
        if category not in self.category_files:
            return
        
        kb_file = self.category_files[category]
        
        if os.path.exists(kb_file):
            with open(kb_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []
        
        new_entry = {
            "brand": brand,
            "product": product,
            "summary": summary,
            "advice": advice
        }
        
        data.append(new_entry)
        
        with open(kb_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ============== Kimi LLM客户端 ==============

class KimiClient:
    """Kimi LLM调用"""
    
    def __init__(self, api_key: str = KIMI_API_KEY, base_url: str = KIMI_BASE_URL, model: str = KIMI_MODEL):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """调用Kimi API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content or ""
    
    def judge_sarcasm(self, text: str, topic: str) -> Dict:
        """判断讽刺评论的真实情感"""
        system_prompt = """你是一个情感分析专家。请分析以下评论的真实情感。
回复格式：
- 真实情感：正面/负面
- 分析理由：xxx
- 置信度：0.0-1.0

注意：如果评论是阴阳怪气/讽刺，请根据字面意思判断真实情感。"""
        
        user_prompt = f"""商品/话题：{topic}
评论：{text}

请判断这条评论的真实情感："""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self.chat(messages)
        
        sentiment = SentimentType.POSITIVE if "正面" in result else SentimentType.NEGATIVE
        
        return {
            "text": text,
            "topic": topic,
            "real_sentiment": sentiment.value,
            "analysis": result
        }
    
    def summarize(self, analysis_results: Dict, category: str) -> str:
        """总结分析结果"""
        system_prompt = """你是一个商品分析专家。请根据以下分析数据，总结该商品的优缺点。
回复格式：
## 综合评价
xxx

## 优点
- xxx
- xxx

## 缺点
- xxx
- xxx

## 购买建议
xxx"""
        
        pos_count = analysis_results.get("positive_count", 0)
        neg_count = analysis_results.get("negative_count", 0)
        sarc_count = analysis_results.get("sarcasm_count", 0)
        llm_judged = analysis_results.get("llm_judged", [])
        
        user_prompt = f"""品类：{category}
好评数量：{pos_count}
差评数量：{neg_count}
讽刺评论数量：{sarc_count}
LLM判断的讽刺评论分析：{json.dumps(llm_judged, ensure_ascii=False)}

请总结分析："""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.chat(messages)
    
    def generate_advice(self, summary: str, knowledge_context: str) -> str:
        """生成购买建议"""
        system_prompt = """你是一个专业的购物顾问。请根据商品分析和知识库信息，给出购买建议。
回复格式：
## 购买建议
建议/不推荐/观望

## 理由
xxx"""
        
        user_prompt = f"""商品分析总结：
{summary}

知识库相关信息：
{knowledge_context}

请给出购买建议："""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.chat(messages)


# ============== 品类分类器 ==============

class CategoryClassifier:
    """商品品类分类器"""
    
    KEYWORDS = {
        "book": ["书", "图书", "小说", "教材", "绘本", "书籍"],
        "tablet": ["平板", "ipad", "平板电脑", "surface", "平板"],
        "electronics": ["手机", "iphone", "安卓", "电脑", "笔记本", "电子产品"],
        "fruit": ["水果", "苹果", "橙子", "芒果", "草莓", "荔枝"],
        "shampoo": ["洗发水", "护发素", "洗头膏", "洗发液"],
        "dairy": ["牛奶", "酸奶", "奶酪", "奶粉", "乳制品"],
        "clothing": ["衣服", "T恤", "衬衫", "裙子", "裤子", "外套", "服装"],
        "water_heater": ["热水器", "电热水器", "燃气热水器"],
        "hotel": ["酒店", "民宿", "宾馆", "客栈", "公寓"],
    }
    
    def classify(self, product_name: str) -> str:
        """通过名称判断品类"""
        for category, keywords in self.KEYWORDS.items():
            if any(kw in product_name for kw in keywords):
                return category
        return "electronics"


# ============== 情感分析器（LoRA） ==============

class SentimentAnalyzer:
    """基于LoRA的情感分析器"""
    
    def __init__(self):
        self.tokenizer = None
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """加载所有品类模型"""
        for category in CATEGORIES:
            model_path = os.path.join(LORA_DIR, category)
            if os.path.exists(model_path):
                try:
                    self.models[category] = {
                        "path": model_path,
                        "model": None,
                        "tokenizer": None
                    }
                except Exception as e:
                    print(f"加载{category}模型失败: {e}")
    
    def _get_model(self, category: str):
        """获取模型（延迟加载）"""
        category = category.lower()
        
        if category not in self.models:
            category = "electronics"
        
        if self.models[category]["model"] is None:
            model_path = self.models[category]["path"]
            base_model = AutoModelForSequenceClassification.from_pretrained(
                CACHE_DIR,
                num_labels=2
            )
            model = PeftModel.from_pretrained(base_model, model_path)
            model = model.merge_and_unload()
            tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
            
            self.models[category]["model"] = model
            self.models[category]["tokenizer"] = tokenizer
        
        return self.models[category]["model"], self.models[category]["tokenizer"]
    
    def analyze(self, text: str, category: str = "electronics") -> SentimentResult:
        """分析单条评论"""
        model, tokenizer = self._get_model(category)
        
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            pred = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][pred].item()
        
        sentiment = SentimentType.POSITIVE if pred == 1 else SentimentType.NEGATIVE
        
        return SentimentResult(
            sentiment=sentiment,
            confidence=confidence,
            original_text=text
        )
    
    def batch_analyze(self, texts: List[str], category: str = "electronics") -> List[SentimentResult]:
        """批量分析"""
        results = []
        for text in texts:
            if text.strip():
                results.append(self.analyze(text, category))
        return results


# ============== 讽刺检测器（TOSPrompt） ==============

class SarcasmDetector:
    """基于TOSPrompt的讽刺检测器"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """加载讽刺检测模型"""
        if os.path.exists(SARCASM_DIR):
            try:
                base_model = AutoModelForSequenceClassification.from_pretrained(
                    CACHE_DIR,
                    num_labels=2
                )
                self.model = PeftModel.from_pretrained(base_model, SARCASM_DIR)
                self.model = self.model.merge_and_unload()
                self.tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
            except Exception as e:
                print(f"加载讽刺检测模型失败: {e}")
    
    def detect(self, text: str, topic: str = "") -> Dict:
        """检测讽刺"""
        if self.model is None:
            return {"is_sarcasm": False, "confidence": 0.0, "text": text}
        
        prompt = f'"{text}" 是对 "{topic}" 的讽刺吗？[MASK]'
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=128)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            
            mask_token_id = self.tokenizer.mask_token_id
            if mask_token_id in inputs.input_ids[0]:
                mask_idx = (inputs.input_ids[0] == mask_token_id).nonzero()[0][0]
                probs = probs[0]
            else:
                probs = probs[0]
            
            pred = torch.argmax(probs, dim=-1).item()
            confidence = probs[pred].item()
        
        is_sarcasm = pred == 1
        
        return {
            "is_sarcasm": is_sarcasm,
            "confidence": confidence,
            "text": text,
            "topic": topic
        }
    
    def batch_detect(self, texts: List[str], topics: List[str] = None) -> List[Dict]:
        """批量检测"""
        results = []
        for i, text in enumerate(texts):
            topic = topics[i] if topics and i < len(topics) else ""
            results.append(self.detect(text, topic))
        return results


# ============== MCP工具服务器 ==============

class MCPToolServer:
    """MCP工具服务器 - 避雷真"""
    
    def __init__(self):
        # 初始化各组件
        self.category_classifier = CategoryClassifier()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sarcasm_detector = SarcasmDetector()
        self.kimi = KimiClient()
        self.knowledge_base = KnowledgeBase()
    
    # ============== MCP工具定义 ==============
    
    def get_mcp_tools(self) -> List[Dict]:
        """获取MCP工具定义（function calling格式）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_product",
                    "description": "搜索淘宝商品",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["keyword"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_comments",
                    "description": "获取商品评论",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string", "description": "商品ID"},
                            "max_count": {"type": "integer", "description": "最大评论数", "default": 100}
                        },
                        "required": ["item_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_xiaohongshu",
                    "description": "搜索小红书避雷笔记",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["keyword"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_heimao",
                    "description": "搜索黑猫投诉记录",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "brand": {"type": "string", "description": "品牌名"}
                        },
                        "required": ["brand"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "classify_category",
                    "description": "根据商品名称判断品类",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string", "description": "商品名称"}
                        },
                        "required": ["product_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "sentiment_analysis",
                    "description": "使用LoRA模型进行情感分析",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "texts": {"type": "array", "items": {"type": "string"}, "description": "评论列表"},
                            "category": {"type": "string", "description": "商品品类"}
                        },
                        "required": ["texts", "category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_sarcasm",
                    "description": "使用TOSPrompt检测讽刺评论",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "texts": {"type": "array", "items": {"type": "string"}, "description": "评论列表"},
                            "topics": {"type": "array", "items": {"type": "string"}, "description": "商品/话题列表"}
                        },
                        "required": ["texts"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "llm_judge_sarcasm",
                    "description": "使用Kimi判断讽刺评论的真实情感",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "评论内容"},
                            "topic": {"type": "string", "description": "商品/话题"}
                        },
                        "required": ["text", "topic"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_knowledge_base",
                    "description": "查询RAG知识库",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "商品品类"},
                            "brand": {"type": "string", "description": "品牌名"},
                            "product": {"type": "string", "description": "商品名"}
                        },
                        "required": ["category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_knowledge_base",
                    "description": "更新RAG知识库",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "商品品类"},
                            "brand": {"type": "string", "description": "品牌名"},
                            "product": {"type": "string", "description": "商品名"},
                            "summary": {"type": "string", "description": "分析总结"},
                            "advice": {"type": "string", "description": "购买建议"}
                        },
                        "required": ["category", "brand", "product", "summary"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "summarize_analysis",
                    "description": "总结分析结果",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis_results": {"type": "object", "description": "分析结果数据"},
                            "category": {"type": "string", "description": "商品品类"}
                        },
                        "required": ["analysis_results", "category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_report",
                    "description": "生成最终避雷报告",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string", "description": "搜索关键词"},
                            "category": {"type": "string", "description": "商品品类"},
                            "comments": {"type": "array", "items": {"type": "string"}, "description": "评论列表"},
                            "sentiment_results": {"type": "object", "description": "情感分析结果"},
                            "sarcasm_results": {"type": "object", "description": "讽刺检测结果"}
                        },
                        "required": ["keyword", "comments"]
                    }
                }
            }
        ]
    
    # ============== MCP工具实现 ==============
    
    def set_driver(self, driver):
        """设置已登录的浏览器实例（解决登录状态问题）"""
        self.external_driver = driver
    
    def _get_taobao_scraper_class(self):
        """获取淘宝爬虫类"""
        try:
            import sys
            aigc_path = r"D:\C_data\SpotTruth\AIGC\Comment_crawling_and_analysis"
            if aigc_path not in sys.path:
                sys.path.insert(0, aigc_path)
            from taobao_new import TaobaoScraperNew
            return TaobaoScraperNew
        except Exception as e:
            print(f"导入淘宝爬虫失败: {e}")
            return None
    
    def search_product(self, brand: str = "", product: str = "", max_results: int = 5, driver=None) -> List[Dict]:
        """搜索淘宝商品
        
        Args:
            brand: 品牌名
            product: 商品名
            max_results: 返回最多多少个商品
            driver: 可选，已登录的浏览器实例
            
        Returns:
            list: 商品列表 [{"name": "商品名称", "url": "商品链接", "price": "价格", "shop": "店铺"}]
        """
        try:
            TaobaoScraperNew = self._get_taobao_scraper_class()
            if not TaobaoScraperNew:
                return []
            
            if driver:
                scraper = TaobaoScraperNew.__new__(TaobaoScraperNew)
                scraper.driver = driver
                products = scraper.search_products(brand, product, max_results)
                return products
            
            with TaobaoScraperNew(
                driver_path=r"E:\edgedriver_win64\msedgedriver.exe"
            ) as scraper:
                scraper.ensure_login()
                products = scraper.search_products(brand, product, max_results)
                return products
        except Exception as e:
            print(f"搜索商品失败: {e}")
            return []
    
    def get_comments(self, url: str = "", brand: str = "", product: str = "", max_count: int = 100, driver=None) -> List[Dict]:
        """获取淘宝商品评论
        
        Args:
            url: 商品详情页链接（优先使用）
            brand: 品牌名（url为空时使用搜索）
            product: 商品名（url为空时使用搜索）
            max_count: 最大评论数
            driver: 可选，已登录的浏览器实例
            
        Returns:
            list: 评论列表 [{"text": "评论内容", "source": "taobao"}]
        """
        try:
            TaobaoScraperNew = self._get_taobao_scraper_class()
            if not TaobaoScraperNew:
                return []
            
            output_file = os.path.join(SCRIPT_DIR, "data", "temp_comments.txt")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            if driver:
                scraper = TaobaoScraperNew.__new__(TaobaoScraperNew)
                scraper.driver = driver
                if url:
                    scraper.scrape_reviews(
                        output_file=output_file,
                        max_comments=max_count,
                        manual_input=False,
                        preset_url=url
                    )
                else:
                    scraper.select_product_and_scrape(
                        brand=brand,
                        product=product,
                        output_file=output_file,
                        max_comments=max_count
                    )
            else:
                with TaobaoScraperNew(
                    driver_path=r"E:\edgedriver_win64\msedgedriver.exe"
                ) as scraper:
                    scraper.ensure_login()
                    if url:
                        scraper.scrape_reviews(
                            output_file=output_file,
                            max_comments=max_count,
                            manual_input=False,
                            preset_url=url
                        )
                    else:
                        scraper.select_product_and_scrape(
                            brand=brand,
                            product=product,
                            output_file=output_file,
                            max_comments=max_count
                        )
            
            comments = []
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        text = line.strip()
                        if text:
                            comments.append({
                                "text": text,
                                "source": "taobao"
                            })
            
            return comments
        except Exception as e:
            print(f"获取评论失败: {e}")
            return []
    
    def search_xiaohongshu(self, keyword: str, max_notes: int = 30, driver=None) -> List[Dict]:
        """搜索小红书避雷笔记
        
        Args:
            keyword: 搜索关键词
            max_notes: 最大笔记数量
            driver: 可选，已登录的浏览器实例
            
        Returns:
            list: 笔记列表 [{"text": "内容", "source": "xiaohongshu"}]
        """
        try:
            import sys
            xhs_path = r"D:\C_data\SpotTruth\AIGC\Comparison_of_similar_products_and_external_link_information"
            if xhs_path not in sys.path:
                sys.path.insert(0, xhs_path)
            from xiaohongshu_scraper import XiaohongshuScraper
            
            output_file = os.path.join(SCRIPT_DIR, "data", "temp_xhs_notes.txt")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            if driver:
                scraper = XiaohongshuScraper.__new__(XiaohongshuScraper)
                scraper.driver = driver
                scraper.scrape_search_results(
                    keyword=keyword,
                    output_file=output_file,
                    max_items=max_notes
                )
            else:
                with XiaohongshuScraper(
                    driver_path=r"E:\edgedriver_win64\msedgedriver.exe"
                ) as scraper:
                    scraper.ensure_login()
                    scraper.scrape_search_results(
                        keyword=keyword,
                        output_file=output_file,
                        max_items=max_notes
                    )
            
            # 读取详情页内容（_desc.txt）
            notes = []
            desc_file = output_file.replace('.txt', '_desc.txt')
            if os.path.exists(desc_file):
                with open(desc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 解析格式：URL: xxx\n内容:\n实际内容
                    entries = content.split('URL:')
                    for entry in entries:
                        if '内容:' in entry:
                            parts = entry.split('内容:')
                            if len(parts) > 1:
                                text = parts[1].strip()
                                if text:
                                    notes.append({
                                        "text": text,
                                        "source": "xiaohongshu"
                                    })
            
            return notes
        except Exception as e:
            print(f"搜索小红书失败: {e}")
            return []
    
    def search_heimao(self, brand: str, max_complaints: int = 50, driver=None) -> List[Dict]:
        """搜索黑猫投诉
        
        Args:
            brand: 品牌名
            max_complaints: 最大投诉数量
            driver: 可选，已登录的浏览器实例
            
        Returns:
            list: 投诉列表 [{"text": "内容", "source": "heimao"}]
        """
        try:
            import sys
            heimao_path = r"D:\C_data\SpotTruth\AIGC\Comparison_of_similar_products_and_external_link_information"
            if heimao_path not in sys.path:
                sys.path.insert(0, heimao_path)
            
            # 写入品牌到文件
            brand_file = os.path.join(heimao_path, "simple_prod_name_with_brand.txt")
            with open(brand_file, 'w', encoding='utf-8') as f:
                f.write(brand)
            
            tousu_file = os.path.join(heimao_path, "tousu.txt")
            
            if driver:
                # 使用传入的driver
                from tousu_crawler import TousuCrawler
                scraper = TousuCrawler.__new__(TousuCrawler)
                scraper.driver = driver
                scraper.keyword = brand
                scraper.max_items = max_complaints
                # 先导航到搜索页面（driver当前可能是首页或登录状态）
                search_url = f"https://tousu.sina.com.cn/index/search/?keywords={brand}&t=1"
                driver.get(search_url)
                time.sleep(3)  # 等待页面加载
                collected = scraper.collect_complaints()
                # 手动写入文件
                with open(tousu_file, 'w', encoding='utf-8') as f:
                    for item in collected:
                        f.write(item + "\n")
            else:
                from tousu_crawler import TousuCrawler
                scraper = TousuCrawler(keyword=brand, max_items=max_complaints)
                collected = scraper.collect_complaints()
                with open(tousu_file, 'w', encoding='utf-8') as f:
                    for item in collected:
                        f.write(item + "\n")
                scraper.driver.quit()
            
            # 读取投诉文件
            complaints = []
            tousu_file = os.path.join(heimao_path, "tousu.txt")
            if os.path.exists(tousu_file):
                with open(tousu_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        text = line.strip()
                        if text:
                            complaints.append({
                                "text": text,
                                "source": "heimao"
                            })
            
            return complaints
        except Exception as e:
            print(f"搜索黑猫投诉失败: {e}")
            return []
    
    def classify_category(self, product_name: str) -> str:
        """品类分类"""
        return self.category_classifier.classify(product_name)
    
    def sentiment_analysis(self, texts: List[str], category: str = "electronics") -> List[Dict]:
        """情感分析"""
        results = self.sentiment_analyzer.batch_analyze(texts, category)
        return [
            {
                "text": r.original_text,
                "sentiment": r.sentiment.value,
                "confidence": r.confidence
            }
            for r in results
        ]
    
    def detect_sarcasm(self, texts: List[str], topics: List[str] = None) -> List[Dict]:
        """讽刺检测"""
        return self.sarcasm_detector.batch_detect(texts, topics)
    
    def llm_judge_sarcasm(self, text: str, topic: str) -> Dict:
        """LLM判断讽刺评论"""
        return self.kimi.judge_sarcasm(text, topic)
    
    def query_knowledge_base(self, category: str, brand: str = "", product: str = "") -> List[Dict]:
        """查询知识库"""
        return self.knowledge_base.query(category, brand, product)
    
    def update_knowledge_base(self, category: str, brand: str, product: str, summary: str, advice: str = ""):
        """更新知识库"""
        self.knowledge_base.update(category, brand, product, summary, advice)
    
    def summarize_analysis(self, analysis_results: Dict, category: str) -> str:
        """总结分析"""
        return self.kimi.summarize(analysis_results, category)
    
    def generate_report(self, 
                       keyword: str, 
                       category: str = "",
                       comments: List[str] = None,
                       sentiment_results: Dict = None,
                       sarcasm_results: Dict = None) -> AnalysisReport:
        """生成综合报告"""
        if comments is None:
            comments = []
        
        if not category:
            category = self.classify_category(keyword)
        
        kb_context = self.knowledge_base.query(category, "", keyword)
        kb_text = json.dumps(kb_context, ensure_ascii=False) if kb_context else ""
        
        sentiment_data = sentiment_results or {}
        sarcasm_data = sarcasm_results or {}
        
        positive_count = sentiment_data.get("positive_count", 0)
        negative_count = sentiment_data.get("negative_count", 0)
        sarcasm_count = sarcasm_data.get("sarcasm_count", 0)
        
        llm_judged = sarcasm_data.get("llm_judged", [])
        
        summary = self.kimi.summarize({
            "positive_count": positive_count,
            "negative_count": negative_count,
            "sarcasm_count": sarcasm_count,
            "llm_judged": llm_judged
        }, category)
        
        advice = self.kimi.generate_advice(summary, kb_text)
        
        return AnalysisReport(
            keyword=keyword,
            category=category,
            total_comments=len(comments),
            positive_count=positive_count,
            negative_count=negative_count,
            sarcasm_count=sarcasm_count,
            llm_judged=llm_judged,
            knowledge_base_context=kb_text,
            summary=summary,
            advice=advice
        )


# ============== 场景工作流 ==============

class ProductWorkflow:
    """商品分析工作流"""
    
    def __init__(self):
        self.server = MCPToolServer()
    
    def run(self, keyword: str, max_comments: int = 100) -> AnalysisReport:
        """执行商品分析流程"""
        
        # 1. 判断品类
        category = self.server.classify_category(keyword)
        
        # 2. 获取评论（淘宝+小红书+黑猫）
        # TODO: 并行调用三个平台
        
        # 3. 情感分析 + 讽刺检测（并行）
        # TODO: 实际调用
        
        # 4. LLM判断讽刺评论
        # TODO: 实际调用
        
        # 5. 查询知识库
        kb_results = self.server.query_knowledge_base(category, "", keyword)
        
        # 6. 生成报告
        report = self.server.generate_report(
            keyword=keyword,
            category=category,
            comments=[],
            sentiment_results={},
            sarcasm_results={}
        )
        
        return report


class BookWorkflow:
    """书评分析工作流"""
    
    def __init__(self):
        self.server = MCPToolServer()
    
    def run(self, keyword: str, max_comments: int = 100) -> Optional[AnalysisReport]:
        """执行书评分析流程"""
        # TODO: 实现书评分析流程
        return None


class HotelWorkflow:
    """酒店分析工作流"""
    
    def __init__(self):
        self.server = MCPToolServer()
    
    def run(self, keyword: str, max_comments: int = 100) -> Optional[AnalysisReport]:
        """执行酒店分析流程"""
        # TODO: 实现酒店分析流程
        return None


# ============== 任务路由器 ==============

class TaskRouter:
    """任务路由器 - 判断场景类型"""
    
    SCENE_KEYWORDS = {
        "product": ["商品", "淘宝", "购买", "东西", "产品"],
        "book": ["书", "图书", "小说", "阅读"],
        "hotel": ["酒店", "民宿", "宾馆", "住宿", "客栈"]
    }
    
    def route(self, input_text: str) -> TaskType:
        """根据输入判断任务类型"""
        for scene, keywords in self.SCENE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in input_text:
                    return TaskType(scene)
        return TaskType.DIRECT
    
    def get_workflow(self, task_type: TaskType):
        """获取对应工作流"""
        workflows = {
            TaskType.PRODUCT: ProductWorkflow,
            TaskType.BOOK: BookWorkflow,
            TaskType.HOTEL: HotelWorkflow
        }
        return workflows.get(task_type, ProductWorkflow)()


# ============== 主函数 ==============

def main():
    """测试MCP工具"""
    server = MCPToolServer()
    router = TaskRouter()
    
    # 获取工具列表
    tools = server.get_mcp_tools()
    print(f"可用MCP工具数量: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['function']['name']}")
    
    # 测试品类分类
    print("\n=== 测试品类分类 ===")
    print(f"iPhone15 -> {server.classify_category('iPhone15')}")
    print(f"洗发水 -> {server.classify_category('海飞丝洗发水')}")
    print(f"酒店 -> {server.classify_category('汉庭酒店')}")


if __name__ == "__main__":
    main()
