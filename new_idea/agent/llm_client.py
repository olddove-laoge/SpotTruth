"""LLM客户端 - 统一封装Kimi API调用"""

import json
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from openai import OpenAI

from config import kimi as kimi_config
from agent.infrastructure import logger, with_retry, ToolError
from agent.models import SentimentType


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str = ""
    tool_calls: List[Dict[str, Any]] = None
    finish_reason: str = ""

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class LLMClient:
    """LLM客户端基类"""

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        raise NotImplementedError

    def judge_sarcasm(self, text: str, topic: str) -> Dict[str, Any]:
        """判断讽刺评论的真实情感"""
        raise NotImplementedError

    def generate_summary(self, analysis_data: Dict[str, Any]) -> str:
        """生成分析总结"""
        raise NotImplementedError

    def generate_advice(self, summary: str, context: str = "") -> str:
        """生成购买建议"""
        raise NotImplementedError


class KimiClient(LLMClient):
    """Kimi API客户端"""

    def __init__(self):
        api_key = kimi_config.api_key or os.getenv("KIMI_API_KEY")
        if not api_key:
            raise ToolError("KIMI_API_KEY未设置")

        self.client = OpenAI(
            api_key=api_key,
            base_url=kimi_config.base_url,
            timeout=kimi_config.timeout
        )
        self.model = kimi_config.model
        self.temperature = kimi_config.temperature
        logger.info(f"KimiClient初始化完成，模型: {self.model}")

    @with_retry(max_retries=2, delay=1.0)
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """调用Kimi API"""
        params = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
        }

        if "tools" in kwargs:
            params["tools"] = kwargs["tools"]

        try:
            response = self.client.chat.completions.create(**params)
            message = response.choices[0].message

            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    })

            return LLMResponse(
                content=message.content or "",
                tool_calls=tool_calls,
                finish_reason=response.choices[0].finish_reason
            )

        except Exception as e:
            logger.error(f"Kimi API调用失败: {e}")
            raise ToolError(f"Kimi API调用失败: {e}")

    def judge_sarcasm(self, text: str, topic: str) -> Dict[str, Any]:
        """判断讽刺评论的真实情感"""
        system_prompt = """你是一个情感分析专家。请分析以下评论的真实情感。

判断规则：
1. 如果是阴阳怪气/讽刺，根据字面意思判断真实情感
2. 如果表面夸但实际是贬，真实情感是负面
3. 如果表面贬但实际是夸，真实情感是正面

回复格式（严格JSON）：
{
    "real_sentiment": "positive" | "negative",
    "confidence": 0.0-1.0,
    "reasoning": "分析理由"
}"""

        user_prompt = f"""商品/话题：{topic}
评论："{text}"

请判断真实情感，以JSON格式回复："""

        try:
            response = self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)

            content = response.content.strip()
            # 尝试提取JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # 标准化sentiment字段
            sentiment = result.get("real_sentiment", "negative")
            if "正面" in sentiment or "positive" in sentiment.lower():
                result["real_sentiment"] = "positive"
            else:
                result["real_sentiment"] = "negative"

            return result

        except json.JSONDecodeError:
            logger.warning(f"LLM返回非JSON格式，使用默认判断: {content[:100]}")
            # 简单关键词判断
            is_positive = any(word in content for word in ["正面", "好评", "positive", "满意", "好"])
            return {
                "real_sentiment": "positive" if is_positive else "negative",
                "confidence": 0.6,
                "reasoning": "基于关键词判断"
            }
        except Exception as e:
            logger.error(f"讽刺判断失败: {e}")
            return {
                "real_sentiment": "negative",
                "confidence": 0.5,
                "reasoning": f"判断出错，默认负面: {e}"
            }

    def generate_summary(self, analysis_data: Dict[str, Any]) -> str:
        """生成分析总结"""
        system_prompt = """你是一个专业的商品分析专家。请根据以下分析数据，生成结构化的分析报告。

输出格式：
## 综合评价
（100字左右的总体评价）

## 主要问题点
- 问题1
- 问题2
...

## 优点
- 优点1
- 优点2
...

## 缺点
- 缺点1
- 缺点2
...

注意：
1. 区分"商品本身问题"和"物流/售后问题"
2. 问题要具体，不要笼统
3. 基于数据说话"""

        stats = analysis_data.get("statistics", {})
        sample_comments = analysis_data.get("sample_comments", [])[:10]

        user_prompt = f"""分析数据：
- 总评论数: {stats.get('total', 0)}
- 好评率: {stats.get('positive_rate', 0):.1%}
- 差评率: {stats.get('negative_rate', 0):.1%}
- 疑似虚假好评（讽刺）: {stats.get('sarcasm_count', 0)}条

样本评论（已分析情感）：
{json.dumps(sample_comments, ensure_ascii=False, indent=2)}

请生成分析报告："""

        try:
            response = self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.7)
            return response.content
        except Exception as e:
            logger.error(f"生成总结失败: {e}")
            return f"生成总结时出错: {e}"

    def generate_advice(self, summary: str, context: str = "") -> str:
        """生成购买建议"""
        system_prompt = """你是一个专业的购物顾问。请根据商品分析结果，给出购买建议。

输出格式：
## 购买建议
[推荐/谨慎考虑/不推荐]

## 适合人群
xxx

## 注意事项
xxx

## 替代建议（如有）
xxx"""

        user_prompt = f"""商品分析：
{summary}

额外信息：
{context}

请给出购买建议："""

        try:
            response = self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.7)
            return response.content
        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            return f"生成建议时出错: {e}"

    def parse_intent(self, user_input: str, history: List[Dict[str, str]], current_product: str = "", analyzed_platforms: List[str] = None) -> Dict[str, Any]:
        """解析用户意图"""

        analyzed_platforms = analyzed_platforms or []

        # 构建上下文信息
        current_info = f"当前正在分析的商品: {current_product}\n" if current_product else "暂无正在分析的商品\n"
        platforms_info = f"已分析的平台: {', '.join(analyzed_platforms) if analyzed_platforms else '无'}\n"
        remaining = []
        if 'taobao' not in analyzed_platforms:
            remaining.append('淘宝')
        if 'xiaohongshu' not in analyzed_platforms:
            remaining.append('小红书')
        if 'heimao' not in analyzed_platforms:
            remaining.append('黑猫投诉')
        remaining_info = f"未分析的平台: {', '.join(remaining) if remaining else '无'}\n"

        system_prompt = f"""你是一个意图识别助手。请分析用户的输入，识别其意图。

{current_info}{platforms_info}{remaining_info}
可能的意图：
1. analyze - 分析某个商品（需要品牌和商品类型）
2. compare - 对比多个商品
3. search_xhs - 只搜索小红书
4. search_heimao - 只搜索黑猫投诉
5. help - 寻求帮助
6. unknown - 无法识别

输出格式（严格JSON）：
{{
    "intent": "analyze|compare|search_xhs|search_heimao|help|unknown",
    "brand": "品牌名（如用户未提供则为空）",
    "product": "商品类型（如用户未提供则为空）",
    "products": [{{"brand": "", "product": ""}}], // 对比时使用
    "need_taobao": true/false,      // 是否需要分析淘宝
    "need_xiaohongshu": true/false, // 是否需要分析小红书
    "need_heimao": true/false,      // 是否需要分析黑猫投诉
    "clarification_needed": true/false,
    "clarification_question": "如果需要澄清，问用户什么"
}}

规则：
1. 如果用户没说品牌名且没有当前商品，必须设置clarification_needed=true
2. 不要猜测品牌名，不确定就问
3. 根据上下文判断用户想分析哪些平台，不要依赖关键词匹配
4. 如果用户提到"它"、"这个商品"、"这个"等代词，结合当前商品理解
5. 如果用户说"那xx呢"、"xx呢"（xx是未分析平台），结合已分析平台理解为继续对比
6. 如果用户未指定平台，且已有已分析平台，询问用户要对比哪个平台

示例：
- 输入: "分析一下德芙巧克力" → intent: "analyze", brand: "德芙", product: "巧克力", need_taobao: true
- 输入: "对比下雀巢咖啡和星巴克咖啡" → intent: "compare", products: 两个商品, need_taobao: true, need_xiaohongshu: true, need_heimao: true
- 输入: "卫龙辣条和麻辣王子哪个好" → intent: "compare", products: 两个商品, need_taobao: true, need_xiaohongshu: true, need_heimao: true
- 输入: "搜索小红书 避雷" → intent: "search_xhs", product: "避雷"
- 输入: "分析雀巢咖啡在小红书的风评" → intent: "analyze", brand: "雀巢", product: "咖啡", need_taobao: false, need_xiaohongshu: true, need_heimao: false
- 输入: "那淘宝呢"（已分析小红书）→ intent: "compare", products: [当前商品], need_taobao: true, need_xiaohongshu: false, need_heimao: false
- 输入: "黑猫投诉怎么样"（已分析小红书）→ intent: "compare", products: [当前商品], need_taobao: false, need_xiaohongshu: false, need_heimao: true"""

        # 构建对话上下文
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-4:]:  # 最近4条
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.chat(messages, temperature=0.3)
            content = response.content.strip()

            # 提取JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # 验证必需字段
            if "intent" not in result:
                result["intent"] = "unknown"

            return result

        except Exception as e:
            logger.error(f"意图解析失败: {e}")
            return {
                "intent": "unknown",
                "brand": "",
                "product": "",
                "clarification_needed": True,
                "clarification_question": "请告诉我您想分析什么商品？（例如：德芙 巧克力）"
            }

    def generate_comparison_conclusion(
        self,
        product_a_name: str,
        product_b_name: str,
        stats_a: Dict,
        stats_b: Dict,
        summary_a: str,
        summary_b: str,
        advice_a: str,
        advice_b: str,
        heimao_analysis_a: Optional[Dict] = None,
        heimao_analysis_b: Optional[Dict] = None,
        xhs_analysis_a: Optional[Dict] = None,
        xhs_analysis_b: Optional[Dict] = None,
        has_taobao_a: bool = False,
        has_taobao_b: bool = False
    ) -> str:
        """生成对比结论 - 由LLM根据数据灵活判断

        重要：基于投诉内容、问题类型、风险等级做判断，而非数量多少。
        关注：食品安全 > 商品质量 > 服务态度
        """
        system_prompt = """你是一位专业的商品口碑分析专家。请根据两款商品的对比数据，生成客观的对比结论和购买建议。

重要原则：
1. 基于投诉/评论的"内容性质"做判断，而非数量多少
2. 风险优先级：食品安全问题 > 商品质量问题 > 服务态度问题
3. 给出明确的购买建议，不要模棱两可
4. 如果是食品/母婴类商品，食品安全问题一票否决
5. 注意区分"未爬取数据"和"已爬取但无数据"的情况

输出格式：
## 对比结论
1. xxx（具体差异点，如"XX存在食品安全投诉，YY仅涉及服务态度"）
2. xxx
...

## 购买建议
[明确建议]：选择XX
[理由]：xxx
[风险提示]：xxx（如适用）"""

        # 构建淘宝数据描述
        def build_taobao_desc(has_data: bool, stats: Dict, summary: str, advice: str) -> str:
            if not has_data:
                return "未爬取淘宝数据"
            total = stats.get('total', 0)
            if total == 0:
                return "已爬取淘宝，但未找到该商品或该商品无评论"
            return f"好评率{stats.get('positive_rate', 0):.0%}，总评论{total}条，疑似虚假好评{stats.get('sarcasm_count', 0)}条\n分析：{summary[:200]}...\n建议：{advice[:150]}..."

        # 构建数据摘要
        data_text = f"""商品A：{product_a_name}
淘宝：{build_taobao_desc(has_taobao_a, stats_a, summary_a, advice_a)}
黑猫投诉：{heimao_analysis_a.get('summary', '无')[:200] if heimao_analysis_a else '无数据'}
投诉类型：{', '.join(heimao_analysis_a.get('complaint_types', [])) if heimao_analysis_a else '无'}
风险等级：{heimao_analysis_a.get('severity', 'unknown') if heimao_analysis_a else 'unknown'}
小红书：{xhs_analysis_a.get('summary', '无')[:200] if xhs_analysis_a else '无数据'}

商品B：{product_b_name}
淘宝：{build_taobao_desc(has_taobao_b, stats_b, summary_b, advice_b)}
黑猫投诉：{heimao_analysis_b.get('summary', '无')[:200] if heimao_analysis_b else '无数据'}
投诉类型：{', '.join(heimao_analysis_b.get('complaint_types', [])) if heimao_analysis_b else '无'}
风险等级：{heimao_analysis_b.get('severity', 'unknown') if heimao_analysis_b else 'unknown'}
小红书：{xhs_analysis_b.get('summary', '无')[:200] if xhs_analysis_b else '无数据'}

请生成对比结论和购买建议："""

        try:
            response = self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data_text}
            ], temperature=0.7)
            return response.content
        except Exception as e:
            logger.error(f"生成对比结论失败: {e}")
            return f"生成对比结论时出错: {e}"
