# agent.py
"""避雷真Agent - 商品口碑分析Agent（LLM驱动版）"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from typing import Any, List, Dict

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from mcp_test.kimi_client import KimiClient
from step6_mcp_tools import MCPToolServer


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_product",
            "description": "搜索淘宝商品，返回商品列表供选择",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "品牌名"},
                    "product": {"type": "string", "description": "商品名"},
                    "max_results": {"type": "integer", "description": "返回商品数量", "default": 5}
                },
                "required": ["brand", "product"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_comments",
            "description": "获取淘宝商品评论",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "商品详情页链接"},
                    "brand": {"type": "string", "description": "品牌名（备用）"},
                    "product": {"type": "string", "description": "商品名（备用）"},
                    "max_count": {"type": "integer", "description": "最大评论数", "default": 100}
                }
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
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "max_notes": {"type": "integer", "description": "最大笔记数", "default": 10}
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
                    "brand": {"type": "string", "description": "品牌名"},
                    "max_complaints": {"type": "integer", "description": "最大投诉数", "default": 10}
                },
                "required": ["brand"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_sarcasm",
            "description": "使用TOSPrompt模型检测评论中的讽刺/阴阳怪气",
            "parameters": {
                "type": "object",
                "properties": {
                    "texts": {"type": "array", "items": {"type": "string"}, "description": "评论列表"},
                    "topics": {"type": "array", "items": {"type": "string"}, "description": "对应的商品/话题列表"}
                },
                "required": ["texts"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sentiment_analysis",
            "description": "使用LoRA模型对评论进行情感分析（正面/负面）",
            "parameters": {
                "type": "object",
                "properties": {
                    "texts": {"type": "array", "items": {"type": "string"}, "description": "评论列表"},
                    "category": {"type": "string", "description": "商品品类（book/tablet/electronics/fruit/shampoo/dairy/clothing/water_heater/hotel）"}
                },
                "required": ["texts", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "classify_category",
            "description": "根据商品名称自动判断商品品类",
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
            "name": "llm_judge_sarcasm",
            "description": "使用Kimi LLM判断讽刺评论的真实情感",
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
            "name": "calculate_sentiment_stats",
            "description": "统一计算好评率/差评率（会自动读取已保存的检测和分析结果）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


class Agent:
    """避雷真Agent - LLM驱动版"""
    
    def __init__(self):
        from typing import Any
        self.kimi = KimiClient()
        self.mcp_server: Any = None
        self.driver: Any = None
        
        # 保存已分析的商品（在当前会话中）
        # 结构: {商品名称: {brand, product, taobao_comments, taobao_result, xiaohongshu_result, heimao_result, ...}}
        self.collected_products = {}
        
        # 独立存储小红书/黑猫数据（不依赖淘宝商品）
        # 结构: {"品牌+商品类型": [笔记列表]}
        self.collected_xiaohongshu = {}
        self.collected_heimao = {}
        
        # 对话历史
        self.conversation_history = []
        
        # 当前正在分析的商品
        self.current_product = ""
        
        # 状态锁，防止并发操作
        self._state_lock = False
    
    def _ensure_product_selected(self) -> bool:
        """确保已选择商品，如果没有则返回False并记录错误"""
        if not self.current_product or self.current_product.strip() == "":
            print("   [错误] 未选择商品，请先搜索并选择商品")
            return False
        return True
    
    def _validate_state_for_analysis(self, tool_name: str) -> str:
        """验证状态是否允许执行分析工具，返回错误信息或空字符串"""
        analysis_tools = ["get_comments", "classify_category", "detect_sarcasm", 
                         "sentiment_analysis", "calculate_sentiment_stats",
                         "search_xiaohongshu", "search_heimao"]
        
        if tool_name in analysis_tools:
            if not self._ensure_product_selected():
                return f"错误：尚未选择商品，无法执行{tool_name}。请先使用search_product搜索商品。"
        return ""
    
    def _call_tool_with_retry(self, func, max_retries: int = 2, *args, **kwargs):
        """带重试的工具调用
        
        Args:
            func: 要调用的函数
            max_retries: 最大重试次数
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果或None
        """
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                # 检查结果是否为空
                if result is None or (isinstance(result, list) and len(result) == 0):
                    if attempt < max_retries:
                        print(f"   ⚠️ 第{attempt+1}次尝试返回空结果，{max_retries - attempt}次重试机会...")
                        continue
                    else:
                        print(f"   ❌ 工具多次返回空结果")
                        return None
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    print(f"   ⚠️ 第{attempt+1}次尝试失败: {str(e)[:50]}，{max_retries - attempt}次重试机会...")
                    import time
                    time.sleep(1)  # 短暂等待后重试
                else:
                    print(f"   ❌ 工具调用最终失败: {str(e)[:100]}")
        
        return {"error": str(last_error) if last_error else "未知错误"}
    
    def _reflect_on_result(self, tool_name: str, result: Any, func_args: dict) -> str:
        """反思机制：验证工具调用结果是否合理
        
        Args:
            tool_name: 工具名称
            result: 工具返回结果
            func_args: 工具参数
            
        Returns:
            反思结果字符串，如果结果合理返回空字符串
        """
        # 1. 检查结果是否为空
        if result is None:
            return f"警告：{tool_name}返回None，可能是API调用失败"
        
        if isinstance(result, (list, dict, str)) and not result:
            return f"警告：{tool_name}返回空结果，请检查参数是否正确或网络是否正常"
        
        # 2. 针对特定工具的检查
        if tool_name == "search_product":
            if isinstance(result, list) and len(result) == 0:
                return f"警告：搜索'{func_args.get('brand', '')} {func_args.get('product', '')}'未找到商品，请尝试其他关键词"
            if isinstance(result, list) and len(result) > 0:
                if not result[0].get("name"):
                    return f"警告：搜索结果缺少商品名称字段"
        
        elif tool_name == "get_comments":
            if isinstance(result, list) and len(result) < 5:
                return f"⚠️ 提示：仅获取到{len(result)}条评论，可能不足以进行准确分析"
        
        elif tool_name == "sentiment_analysis":
            if isinstance(result, list) and len(result) == 0:
                return f"警告：情感分析返回空结果，可能模型加载失败"
            # 检查是否有高置信度的结果
            if isinstance(result, list):
                low_confidence_count = sum(1 for r in result if isinstance(r, dict) and r.get("confidence", 1.0) < 0.6)
                if low_confidence_count > len(result) * 0.5:
                    return f"⚠️ 提示：{low_confidence_count}条结果置信度较低，建议复核"
        
        # 3. 检查错误标记
        if isinstance(result, dict) and result.get("error"):
            return f"错误：{result.get('error')}"
        
        return ""  # 结果合理
        
    def welcome(self):
        """开场白"""
        print("\n" + "="*60)
        print("🤖 避雷真 - 商品口碑分析Agent")
        print("="*60)
        print("您好！我是避雷真，一个专业的商品口碑分析助手。")
        print("")
        print("我可以帮您：")
        print("  📊 分析淘宝商品的好评率/差评率")
        print("  🔍 识别虚假好评和阴阳怪气评价")
        print("  📝 提供购买建议")
        print("  🔄 对比多个商品")
        print("")
        print("使用方法：")
        print("  • 输入商品链接（如 https://item.taobao.com/...）")
        print("  • 输入品牌名+商品名（如 蓝月亮 洗衣液）")
        print("  • 问之前分析过的商品怎么样")
        print("")
        print("输入 'quit' 或 '退出' 结束程序")
        print("="*60 + "\n")
    
    def get_system_prompt(self) -> str:
        """获取系统提示词 - 完整的CoT优化版"""
        
        # 只显示当前正在分析的商品
        current_info = ""
        if self.current_product:
            data = self.collected_products.get(self.current_product, {})
            taobao_result = data.get("taobao_result") or data.get("taobao_stats") or {}
            
            if isinstance(taobao_result, dict) and taobao_result:
                positive_rate = taobao_result.get("positive_rate", taobao_result.get("好评率", "N/A"))
                negative_rate = taobao_result.get("negative_rate", taobao_result.get("差评率", "N/A"))
                current_info = f"\n## 当前分析的商品的简要信息\n"
                current_info += f"- 商品：{self.current_product}\n"
                current_info += f"- 好评率：{positive_rate}，差评率：{negative_rate}\n"
            else:
                current_info = f"\n## 当前分析的商品的简要信息\n- 商品：{self.current_product}\n(暂无分析结果)"
        else:
            current_info = "\n暂无正在分析的商品。"
        
        return f"""你是"避雷真"，一个专业的商品口碑分析助手。

## 你的核心能力
1. 分析淘宝商品的好评率/差评率
2. 识别虚假好评和阴阳怪气评价（反讽检测）
3. 搜索小红书避雷笔记
4. 搜索黑猫投诉记录
5. 提供购买建议

## 工具描述（重要！按描述使用）

### search_product
- 用途：搜索淘宝商品
- 【必须】传入brand（品牌名）和product（商品类型）
- 【重要】如果用户没有明确说品牌，必须先问用户！

### get_comments
- 用途：获取淘宝商品评论
- 【必须】需要商品链接（url字段），或通过search_product获取
- 【前置】必须先调用search_product获取商品链接

### search_xiaohongshu
- 用途：搜索小红书避雷笔记
- 【必须】传入brand（品牌名）+product（商品类型），如"德芙 巧克力"
- 【重要】不能只搜品牌名，会混淆！

### search_heimao
- 用途：搜索黑猫投诉
- 【必须】传入brand（品牌名）+product（商品类型）
- 【重要】需要品类过滤，否则会把不同业务的同名品牌混进来

### detect_sarcasm
- 用途：检测评论是否为讽刺/阴阳怪气
- 【输入】评论文本列表
- 【前置】需要先获取评论

### sentiment_analysis
- 用途：分析评论情感（好评/差评）
- 【输入】评论文本列表 + 商品品类
- 【前置】需要先获取评论

### classify_category
- 用途：判断商品品类（book/tablet/electronics/fruit/shampoo/dairy/clothing/water_heater/hotel）
- 【输入】商品名称

### llm_judge_sarcasm
- 用途：判断讽刺评论的真实情感（是好评还是差评伪装成好评）
- 【前置】需要先调用detect_sarcasm识别出讽刺评论

### calculate_sentiment_stats
- 用途：计算好评率/差评率
- 【前置】需要先有detect_sarcasm和sentiment_analysis的结果

## ========== 核心推理流程（CoT）==========

### 【重要】品牌名处理规则
1. 如果用户说"分析巧克力"但没说品牌 → 必须问："请问您想分析哪个品牌？"
2. 如果用户说"对比X" → 必须问："您想对比哪些品牌？"
3. 绝对不能自己猜测品牌名！

### 【重要】问题分类规则
分析评论时，请区分以下问题类型：
1. **商品本身问题**：质量差、假货、口味不好、过期 → 计入商品差评
2. **物流/快递问题**：发货慢、包装破损、快递丢失 → 不计入商品差评，单独标注"物流问题"
3. **售后服务问题**：客服态度差、退换货难 → 单独标注"售后问题"
4. **商品问题**：商品损坏、功能异常 → 计入商品差评

### 【重要】数据源匹配规则
- 小红书：搜索关键词 = 品牌名 + 商品类型（如"德芙 巧克力"），不能只搜"德芙"
- 黑猫投诉：搜索关键词 = 品牌名 + 商品类型，需要过滤掉不相关投诉

### 推理步骤（按顺序执行）

**阶段1：确认用户意图**
1. 用户想要分析/对比/了解什么？
2. 用户是否说了具体品牌？没有 → 必须先问！

**阶段2：收集数据**
1. 调用search_product获取商品（如果用户给了品牌+商品）
2. 调用get_comments获取淘宝评论
3. 调用classify_category判断品类

**阶段3：分析数据**
1. 调用detect_sarcasm检测讽刺评论
2. 对讽刺评论 → 调用llm_judge_sarcasm
3. 对正常评论 → 调用sentiment_analysis
4. 调用calculate_sentiment_stats计算好评率/差评率

**阶段4：补充信息（需要用户确认）**
- 询问用户是否需要小红书/黑猫信息
- 如果需要 → 分别调用search_xiaohongshu和search_heimao

**阶段5：生成报告**
- 整合所有数据，生成分析报告
- 区分"商品问题"和"物流/售后问题"

## Few-Shot示例（参考学习）

### 示例1：用户没有说品牌
用户输入："帮我分析巧克力"
思考：用户没有说具体品牌，我不能自己猜测。
行动：回复"请问您想分析哪个品牌的巧克力？比如德芙、费列罗、士力架等？"

### 示例2：用户说了品牌和商品
用户输入："分析德芙巧克力"
思考：用户给了品牌"德芙"和商品"巧克力"，我可以开始搜索。
行动：调用search_product(brand="德芙", product="巧克力")

### 示例3：对比场景
用户输入："对比德芙和费列罗的巧克力"
思考：用户想对比两个品牌，需要分别分析。
行动：
1. 先说"好的，我来帮您对比德芙和费列罗的巧克力"
2. 先分析德芙：调用search_product → get_comments → detect_sarcasm → sentiment_analysis
3. 再分析费列罗：同样流程
4. 最后对比结果

### 示例4：区分问题类型
用户输入："这个巧克力怎么样"
分析评论时发现：
- "味道不错" → 好评
- "发货太慢了" → 物流问题，不计入商品差评
- "客服态度很差" → 售后问题，单独标注
- "巧克力是假的" → 商品本身问题，计入差评

### 示例5：灵活使用单个功能
用户输入："帮我搜一下德芙巧克力的小红书避雷"
思考：用户只需要小红书信息，不需要淘宝评论分析
行动：直接调用search_xiaohongshu(brand="德芙", product="巧克力")

用户输入："看看这个商品的黑猫投诉"
思考：用户只需要黑猫投诉信息
行动：调用search_heimao(brand="品牌名", product="商品类型")

用户输入："帮我找找这个商品的淘宝评论"
思考：用户只想获取评论，不需要分析
行动：调用search_product获取商品，然后调用get_comments获取评论

## 灵活使用模式
【重要】用户可能只需要某个单一功能，不要强制走完整流程！
- 如果用户只问小红书 → 只调用search_xiaohongshu
- 如果用户只问黑猫 → 只调用search_heimao
- 如果用户只想要评论 → 调用search_product + get_comments
- 如果用户要完整分析 → 按完整流程走

但是：
- 如果用户没说品牌名，仍然必须先问！

## 【重要】如何利用已有数据
在你调用任何工具之前，必须先检查是否已经有相关数据！

### 检查步骤
1. 搜索小红书之前 → 检查 self.collected_xiaohongshu 中是否已有该关键词的数据
2. 搜索黑猫之前 → 检查 self.collected_heimao 中是否已有该品牌的数据
3. 获取淘宝评论之前 → 检查 self.collected_products[当前商品].taobao_comments 是否已有

### 如果已有数据
- 不要重新爬取！直接对已有数据进行分析
- 例如：用户说"请分析小红书内容"，先检查是否有数据，有的话直接分析

### 分析要求
- 拿到小红书/黑猫数据后，必须进行【深度分析】，不能直接返回原始内容
- 要提取：主要负面观点、避坑点、用户抱怨最多的问题
- 总结成有结构的分析报告

## 重要规则
1. 【必须】用户没说品牌 → 必须先问，不能猜测！
2. 【必须】每次工具调用后检查结果是否为空
3. 【必须】区分商品问题和物流/售后问题
4. 【必须】小红书/黑猫搜索要包含商品类型，不能只搜品牌
5. 分析完一个商品后才能分析下一个（但可以同时分析另一个品牌的同类商品）

## 当前状态
{current_info}

## 输出格式
- 直接回复用户，不要输出工具调用过程
- 用友好、专业的语气回复
- 如果需要用户确认什么事情，明确提问"""
    
    def save_product_result(self, product_name: str, result_data: dict):
        """保存当前会话的商品分析结果"""
        self.collected_products[product_name] = result_data
    
    def clear_session(self):
        """清除当前会话的记忆（类似opencode的新会话）"""
        self.collected_products = {}
        self.current_product = ""
        self.conversation_history = []
        print("   🧹 已清除当前会话记忆")
    
    def load_last_session(self):
        """加载上一个会话的结果（可选，只加载最近1个）"""
        cache_file = os.path.join(os.path.dirname(__file__), "data", "last_session.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 只加载最近一个商品
                if data.get("product_name"):
                    self.collected_products[data["product_name"]] = data.get("result", {})
                    print(f"\n📂 已恢复上一会话: {data.get('product_name')}")
            except Exception as e:
                print(f"   [警告] 加载上一会话失败: {e}")
    
    def save_last_session(self):
        """保存当前会话到文件（只保存最近1个）"""
        if not self.current_product:
            return
            
        cache_file = os.path.join(os.path.dirname(__file__), "data", "last_session.json")
        
        try:
            data = {
                "product_name": self.current_product,
                "result": self.collected_products.get(self.current_product, {}),
                "timestamp": time.time()
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   [警告] 保存会话失败: {e}")
    
    def recognize_intent_and_act(self, user_input: str) -> str:
        """LLM自主决策如何处理用户输入"""
        
        # 构建消息
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
        ]
        
        # 添加对话历史（最近5轮）
        for msg in self.conversation_history[-10:]:
            messages.append(msg)
        
        # 添加当前输入
        messages.append({"role": "user", "content": user_input})
        
        # LLM决定如何响应
        consecutive_empty_results = 0  # 连续空结果计数
        max_empty_rounds = 3  # 连续3轮空结果则退出
        
        for turn in range(15):  # 最多15轮工具调用
            response = self.kimi.chat(messages, tools=TOOLS)
            
            if response.get("tool_calls"):
                tool_call = response["tool_calls"][0]
                func_name = tool_call["name"]
                
                # 调试：打印原始 arguments
                raw_args = tool_call["arguments"]
                print(f"   [调试] raw_args长度: {len(raw_args) if isinstance(raw_args, str) else 'dict'}")
                
                try:
                    func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON解析失败: {e}")
                    print(f"   [调试] 原始内容: {raw_args[:500]}...")
                    # 跳过失败的调用
                    messages.append({"role": "user", "content": f"工具参数解析失败，请重新调用。"})
                    continue
                
                print(f"\n🔧 调用工具: {func_name}")
                print(f"   参数: {json.dumps(func_args, ensure_ascii=False)[:100]}...")
                
                # 执行工具
                try:
                    if func_name == "search_product":
                        result = self.mcp_server.search_product(
                            brand=func_args.get("brand", ""),
                            product=func_args.get("product", ""),
                            max_results=func_args.get("max_results", 5),
                            driver=self.driver
                        )
                        
                        # 明确检查结果，设置current_product
                        if result and len(result) > 0:
                            selected_product = result[0].get("name", "")
                            if selected_product:
                                self.current_product = selected_product
                                self.collected_products[self.current_product] = {
                                    "brand": func_args.get("brand", ""),
                                    "product": func_args.get("product", ""),
                                    "product_info": result[0]
                                }
                                print(f"   ✅ 已选择商品: {self.current_product}")
                            else:
                                print("   [警告] 商品列表返回为空，未找到有效商品名称")
                        else:
                            print("   [警告] 搜索结果为空，请尝试其他关键词")
                        
                    elif func_name == "get_comments":
                        url = func_args.get("url", "")
                        brand = func_args.get("brand", "")
                        product = func_args.get("product", "")
                        
                        result = self.mcp_server.get_comments(
                            url=url,
                            brand=brand,
                            product=product,
                            max_count=func_args.get("max_count", 100),
                            driver=self.driver
                        )
                        
                        if result and self.current_product:
                            if "taobao_comments" not in self.collected_products[self.current_product]:
                                self.collected_products[self.current_product]["taobao_comments"] = []
                            self.collected_products[self.current_product]["taobao_comments"].extend(result)
                            
                    elif func_name == "classify_category":
                        result = self.mcp_server.classify_category(
                            product_name=func_args.get("product_name", "")
                        )
                        if self.current_product:
                            self.collected_products[self.current_product]["category"] = result
                            
                    elif func_name == "detect_sarcasm":
                        result = self.mcp_server.detect_sarcasm(
                            texts=func_args.get("texts", []),
                            topics=func_args.get("topics", [])
                        )
                        if self.current_product:
                            self.collected_products[self.current_product]["sarcasm_results"] = result
                            
                    elif func_name == "sentiment_analysis":
                        category = func_args.get("category")
                        if not category and self.current_product:
                            category = self.collected_products.get(self.current_product, {}).get("category", "electronics")
                        result = self.mcp_server.sentiment_analysis(
                            texts=func_args.get("texts", []),
                            category=category or "electronics"
                        )
                        if self.current_product:
                            if "sentiment_results" not in self.collected_products[self.current_product]:
                                self.collected_products[self.current_product]["sentiment_results"] = []
                            self.collected_products[self.current_product]["sentiment_results"].extend(result)
                            
                    elif func_name == "llm_judge_sarcasm":
                        result = self.mcp_server.llm_judge_sarcasm(
                            text=func_args.get("text", ""),
                            topic=func_args.get("topic", "")
                        )
                        
                    elif func_name == "calculate_sentiment_stats":
                        # 直接从已存储的数据获取
                        product_data = self.collected_products.get(self.current_product, {})
                        sarcasm_results = product_data.get("sarcasm_results", [])
                        sentiment_results = product_data.get("sentiment_results", [])
                        result = self.mcp_server.calculate_sentiment_stats(
                            sarcasm_results=sarcasm_results,
                            sentiment_results=sentiment_results
                        )
                        if self.current_product:
                            self.collected_products[self.current_product]["taobao_stats"] = result
                        
                    elif func_name == "search_xiaohongshu":
                        result = self.mcp_server.search_xiaohongshu(
                            keyword=func_args.get("keyword", ""),
                            max_notes=func_args.get("max_notes", 10),
                            driver=self.driver
                        )
                        # 独立存储小红书数据，不依赖current_product
                        keyword = func_args.get("keyword", "")
                        self.collected_xiaohongshu[keyword] = result
                        
                    elif func_name == "search_heimao":
                        result = self.mcp_server.search_heimao(
                            brand=func_args.get("brand", ""),
                            max_complaints=func_args.get("max_complaints", 10),
                            driver=self.driver
                        )
                        # 独立存储黑猫数据
                        brand = func_args.get("brand", "")
                        self.collected_heimao[brand] = result
                            
                    else:
                        result = "未知工具"
                    
                    # 记录工具调用
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": f"call_{turn}",
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": json.dumps(func_args)
                            }
                        }]
                    })
                    
                    # 检查结果是否为空
                    if not result or (isinstance(result, (list, dict)) and len(result) == 0):
                        # 工具返回空结果，需要告知LLM
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}",
                            "content": f"[失败] {func_name}返回空结果，请检查参数或重试"
                        })
                        print(f"   ⚠️ 工具返回空结果")
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}",
                            "content": f"成功: {str(result)[:500]}"
                        })
                    
                    # 反思机制：检查结果是否合理
                    reflection = self._reflect_on_result(func_name, result, func_args)
                    if reflection:
                        print(f"   💡 {reflection}")
                        # 将反思结果告知LLM
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}_reflection",
                            "content": reflection
                        })
                    
                    # 保存当前分析结果到缓存
                    if self.current_product and self.current_product in self.collected_products:
                        self.save_product_result(self.current_product, self.collected_products[self.current_product])
                    
                    print(f"   ✅ 完成")
                    
                except Exception as e:
                    print(f"   ❌ 工具调用失败: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": f"call_{turn}",
                        "content": f"错误: {str(e)}"
                    })
                    consecutive_empty_results += 1
            else:
                # LLM直接回复，不调用工具
                content = response.get("content", "")
                
                # 检查是否有实质性内容
                if content and len(content.strip()) > 10:
                    consecutive_empty_results = 0  # 重置计数器
                else:
                    consecutive_empty_results += 1
                
                # 连续多次无实质进展则退出
                if consecutive_empty_results >= max_empty_rounds:
                    print(f"   [警告] 连续{max_empty_rounds}轮无实质进展，退出循环")
                    return "抱歉，我无法完成您的请求。请尝试更具体地描述您的需求。"
                
                # 保存对话历史（限制为最近20条，即10轮）
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": content})
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                return content
            
            # 连续空结果检查
            if consecutive_empty_results >= max_empty_rounds:
                print(f"   [警告] 连续{max_empty_rounds}轮工具调用无有效结果，退出循环")
                break
        
        return "抱歉，我需要更多时间来思考这个问题。请稍后再试。"
    
    def run(self):
        """运行Agent"""
        self.welcome()
        
        # 加载上一会话结果（可选）
        self.load_last_session()
        
        print("\n👤 您: ", end="")
        
        while True:
            try:
                user_input = input().strip()
                
                if not user_input:
                    print("\n👤 您: ", end="")
                    continue
                
                if user_input.lower() in ["quit", "退出", "q"]:
                    self.save_last_session()  # 保存当前会话
                    print("\n👋 再见！\n")
                    break
                
                # LLM自主处理
                response = self.recognize_intent_and_act(user_input)
                
                print(f"\n🤖 避雷真: {response}")
                print("\n👤 您: ", end="")
                
            except KeyboardInterrupt:
                self.save_last_session()  # 保存当前会话
                print("\n\n👋 再见！\n")
                break
            except Exception as e:
                print(f"\n❌ 出错: {e}")
                import traceback
                traceback.print_exc()
                print("\n👤 您: ", end="")


def main():
    # 初始化浏览器
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    profile_dir = r"C:\unified_bot_profile"
    
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    print("正在启动浏览器...")
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        # 登录淘宝
        print("\n[1/3] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        # 登录小红书（可选）
        print("\n[2/3] 打开小红书，请登录...")
        driver.get("https://www.xiaohongshu.com")
        input("  登录完成后，按回车继续...")
        
        # 登录黑猫投诉（可选）
        print("\n[3/3] 打开黑猫投诉，请登录...")
        driver.get("https://tousu.sina.com.cn")
        input("  登录完成后，按回车继续...")
        
        # 初始化Agent
        print("\n初始化Agent...")
        agent = Agent()
        agent.driver = driver
        agent.mcp_server = MCPToolServer()
        
        # 运行
        agent.run()
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
