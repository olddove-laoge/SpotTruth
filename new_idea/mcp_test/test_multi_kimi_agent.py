# test_multi_kimi_agent.py
"""多Kimi协作分析 - 主控Kimi收集数据，子Kimi分别分析"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from mcp_test.kimi_client import KimiClient
from step6_mcp_tools import MCPToolServer


class ToolCallTracker:
    """工具调用追踪器"""
    
    def __init__(self, log_file: str = None):
        self.calls = []
        self.start_time = datetime.now()
        self.log_file = log_file or f"tool_calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def record(self, phase: str, tool_name: str, args: dict = None, result_preview: str = None):
        """记录工具调用"""
        call = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "phase": phase,
            "tool": tool_name,
            "args": args,
            "result_preview": result_preview[:200] if result_preview else None
        }
        self.calls.append(call)
        print(f"\n📝 [{phase}] 调用工具: {tool_name}")
        
    def save(self):
        """保存到文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_calls": len(self.calls),
                "calls": self.calls
            }, f, ensure_ascii=False, indent=2)
        print(f"\n📁 工具调用日志已保存: {self.log_file}")
        
    def print_summary(self):
        """打印汇总"""
        print(f"\n{'='*60}")
        print(f"📊 工具调用汇总 (共 {len(self.calls)} 次)")
        print(f"{'='*60}")
        
        phases = {}
        for call in self.calls:
            p = call["phase"]
            phases[p] = phases.get(p, 0) + 1
            
        for p, count in phases.items():
            print(f"  {p}: {count} 次")
        print(f"{'='*60}")


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
                    "url": {"type": "string", "description": "商品详情页链接（优先使用）"},
                    "brand": {"type": "string", "description": "品牌名（url为空时使用搜索）"},
                    "product": {"type": "string", "description": "商品名（url为空时使用搜索）"},
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
                    "max_notes": {"type": "integer", "description": "最大笔记数", "default": 30}
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
                    "max_complaints": {"type": "integer", "description": "最大投诉数", "default": 50}
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
    }
]


class MultiKimiAgent:
    """多Kimi协作分析器"""
    
    def __init__(self, tracker: ToolCallTracker = None):
        self.main_kimi = KimiClient()  # 主控Kimi
        self.taobao_kimi = KimiClient()  # 淘宝评论分析Kimi (分析内容)
        self.taobao_classify_kimi = KimiClient()  # 淘宝评论分类Kimi (判断反讽)
        self.xiaohongshu_kimi = KimiClient()  # 小红书分析Kimi
        self.heimao_kimi = KimiClient()  # 黑猫投诉分析Kimi
        self.sarcasm_kimi = KimiClient()  # 判断反讽评论真实情感的Kimi
        
        self.tracker = tracker  # 工具调用追踪器
        
        self.collected_data = {
            "product_info": None,
            "product_name": "",
            "category": "electronics",
            "taobao_comments": [],
            "xiaohongshu_notes": [],
            "heimao_complaints": []
        }
        
    def collect_data(self, tool_functions: dict, brand: str, product: str, driver) -> bool:
        """主控Kimi收集数据"""
        print("\n" + "="*60)
        print("📥 阶段1: 主控Kimi收集数据")
        print("="*60)
        
        system_prompt = """你是一个专业的商品分析助手。
用户要分析商品口碑，你需要按顺序完成以下数据收集步骤：

1. 搜索淘宝商品（search_product，品牌=brand，商品=product）
2. 获取淘宝商品评论（get_comments，使用上一步得到的商品链接）
3. 搜索小红书相关笔记（search_xiaohongshu，关键词=品牌+商品）
4. 搜索黑猫投诉记录（search_heimao，品牌=brand）
5. 判断商品品类（classify_category，使用商品名称）

完成数据收集后，直接输出"数据收集完成"。"""
        
        user_msg = f"帮我分析{brand}{product}怎么样"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
        
        for turn in range(12):
            response = self.main_kimi.chat(messages, tools=TOOLS)
            
            if response["tool_calls"]:
                tool_call = response["tool_calls"][0]
                func_name = tool_call["name"]
                func_args = json.loads(tool_call["arguments"]) if isinstance(tool_call["arguments"], str) else tool_call["arguments"]
                
                print(f"\n[主控Kimi调用] {func_name}")
                
                if func_name in tool_functions:
                    try:
                        result = tool_functions[func_name](**func_args)
                        
                        # 记录工具调用
                        if self.tracker:
                            self.tracker.record("阶段1-数据收集", func_name, func_args, f"获取{len(result) if result else 0}条数据")
                        
                        if func_name == "search_product" and result:
                            self.collected_data["product_info"] = result[0]
                            self.collected_data["product_name"] = result[0].get("name", "")
                            print(f"   → 商品: {result[0]['name']}")
                        elif func_name == "get_comments" and result:
                            self.collected_data["taobao_comments"] = result
                            print(f"   → 获取评论: {len(result)} 条")
                        elif func_name == "search_xiaohongshu" and result:
                            self.collected_data["xiaohongshu_notes"] = result
                            print(f"   → 获取小红书: {len(result)} 条")
                        elif func_name == "search_heimao" and result:
                            self.collected_data["heimao_complaints"] = result
                            print(f"   → 获取黑猫投诉: {len(result)} 条")
                        elif func_name == "classify_category" and result:
                            self.collected_data["category"] = result
                            print(f"   → 品类: {result}")
                        
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
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}",
                            "content": f"成功: {str(result)[:100]}"
                        })
                    except Exception as e:
                        print(f"   ❌ 工具调用失败: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}",
                            "content": f"错误: {str(e)}"
                        })
            else:
                if response["content"] and "数据收集完成" in response["content"]:
                    print(f"\n✅ 数据收集完成")
                    return True
                elif response["content"]:
                    messages.append({"role": "assistant", "content": response["content"]})
        
        return False
    
    def analyze_taobao_classify(self, tool_functions: dict) -> str:
        """淘宝评论分类：反讽检测 + LoRA情感分析 → 好评率/差评率"""
        print("\n" + "="*60)
        print("🔍 阶段2.1.1: 淘宝评论分类 (反讽+LoRA)")
        print("="*60)
        
        comments = self.collected_data["taobao_comments"]
        if not comments:
            return '{"error": "无评论数据"}'
        
        product_name = self.collected_data["product_name"]
        category = self.collected_data["category"]
        
        comment_texts = [c.get("text", "") for c in comments]
        topics = [product_name] * len(comment_texts)
        
        # 1. 反讽检测
        print(f"\n[1] 反讽检测中 ({len(comment_texts)} 条评论)...")
        try:
            sarcasm_result = tool_functions["detect_sarcasm"](comment_texts, topics)
        except Exception as e:
            print(f"   ❌ 反讽检测失败: {e}")
            sarcasm_result = [{"is_sarcastic": False, "confidence": 0.0} for _ in comment_texts]
        
        sarcastic_comments = []
        normal_comments = []
        
        for i, result in enumerate(sarcasm_result):
            if result.get("is_sarcastic", False):
                sarcastic_comments.append({
                    "text": comment_texts[i],
                    "topic": product_name
                })
            else:
                normal_comments.append(comment_texts[i])
        
        if self.tracker:
            self.tracker.record("阶段2.1-淘宝分类", "detect_sarcasm", {"count": len(comment_texts)}, f"反讽:{len(sarcastic_comments)}, 正常:{len(normal_comments)}")
        
        print(f"   反讽评论: {len(sarcastic_comments)} 条")
        print(f"   正常评论: {len(normal_comments)} 条")
        
        # 2. 反讽评论 → Kimi判断真实情感
        sarcastic_positive = 0
        sarcastic_negative = 0
        
        if sarcastic_comments:
            print(f"\n[2] Kimi判断反讽评论真实情感 ({len(sarcastic_comments)} 条)...")
            for i, sc in enumerate(sarcastic_comments):
                try:
                    result = tool_functions["llm_judge_sarcasm"](sc["text"], sc["topic"])
                    if self.tracker:
                        self.tracker.record("阶段2.1-淘宝分类", "llm_judge_sarcasm", {"text": sc["text"][:50]}, f"结果:{result.get('sentiment')}")
                    sentiment = result.get("sentiment", "neutral")
                    if sentiment == "positive":
                        sarcastic_positive += 1
                    else:
                        sarcastic_negative += 1
                except Exception as e:
                    print(f"   [{i+1}] 判断失败: {e}")
        
        # 3. 正常评论 → LoRA情感分析
        normal_positive = 0
        normal_negative = 0
        
        if normal_comments:
            print(f"\n[3] LoRA模型情感分析 ({len(normal_comments)} 条)...")
            batch_size = 50
            for i in range(0, len(normal_comments), batch_size):
                batch = normal_comments[i:i+batch_size]
                try:
                    lora_result = tool_functions["sentiment_analysis"](batch, category)
                    if self.tracker:
                        self.tracker.record("阶段2.1-淘宝分类", "sentiment_analysis", {"count": len(batch), "category": category}, f"正面:{normal_positive}, 负面:{normal_negative}")
                    for r in lora_result:
                        if r.get("sentiment") == "positive":
                            normal_positive += 1
                        else:
                            normal_negative += 1
                except Exception as e:
                    print(f"   批次{i//batch_size + 1}失败: {e}")
        
        # 4. 合并结果
        total_positive = sarcastic_positive + normal_positive
        total_negative = sarcastic_negative + normal_negative
        total = total_positive + total_negative
        
        好评率 = round(total_positive / total * 100, 1) if total > 0 else 0
        差评率 = round(total_negative / total * 100, 1) if total > 0 else 0
        
        print(f"\n[4] 淘宝评论分类结果:")
        print(f"   总评论数: {total}")
        print(f"   ✅ 好评率: {好评率}%")
        print(f"   ❌ 差评率: {差评率}%")
        
        return json.dumps({
            "总评论数": total,
            "好评率": f"{好评率}%",
            "差评率": f"{差评率}%",
            "反讽评论数": len(sarcastic_comments),
            "正常评论数": len(normal_comments)
        }, ensure_ascii=False)
    
    def analyze_taobao_content(self) -> str:
        """淘宝评论内容分析：由Kimi分析评论内容"""
        print("\n" + "="*60)
        print("🔍 阶段2.1.2: 淘宝评论内容分析 (Kimi)")
        print("="*60)
        
        comments = self.collected_data["taobao_comments"]
        if not comments:
            return '{"error": "无评论数据"}'
        
        comment_texts = [c.get("text", "") for c in comments[:30]]
        
        prompt = f"""你是一个专业的商品评论分析师。

请分析以下淘宝评论内容，要求：
1. 总结用户最常提到的优点（口味、品质、包装等）
2. 找出用户最常抱怨的问题
3. 分析不同口味的受欢迎程度

淘宝评论：
{chr(10).join([f"{i+1}. {text}" for i, text in enumerate(comment_texts)])}

请输出JSON格式的分析结果：
{{
    "主要优点": ["优点1", "优点2", "优点3"],
    "主要问题": ["问题1", "问题2", "问题3"],
    "口味评价": {{
        "受欢迎口味": ["口味1", "口味2"],
        "不受欢迎口味": ["口味3"]
    }},
    "总结": "一句话总结"
}}"""
        
        response = self.taobao_kimi.chat([
            {"role": "user", "content": prompt}
        ])
        
        result = response.get("content", "")
        print(f"淘宝评论内容分析:\n{result[:300]}...")
        return result
    
    def analyze_xiaohongshu(self) -> str:
        """子Kimi2: 分析小红书笔记"""
        print("\n" + "="*60)
        print("🔍 阶段2.2: Kimi2 分析小红书笔记")
        print("="*60)
        
        notes = self.collected_data["xiaohongshu_notes"]
        if not notes:
            return '{"error": "无小红书数据"}'
        
        note_texts = [n.get("text", "") for n in notes[:10]]
        
        prompt = f"""你是一个专业的小红书内容分析师。

请分析以下小红书笔记内容，要求：
1. 总结用户对商品的主要评价（正面/负面）
2. 找出用户经常提到的"坑"或注意事项
3. 分析不同口味的受欢迎程度

小红书笔记：
{chr(10).join([f"笔记{i+1}: {text[:200]}..." for i, text in enumerate(note_texts)])}

请输出JSON格式的分析结果：
{{
    "总体评价": "正面/负面/中性",
    "正面内容": ["优点1", "优点2"],
    "负面内容": ["问题1", "问题2"],
    "避坑建议": ["建议1", "建议2"],
    "口味推荐": ["推荐口味", "不推荐口味"],
    "总结": "一句话总结"
}}"""
        
        response = self.xiaohongshu_kimi.chat([
            {"role": "user", "content": prompt}
        ])
        
        result = response.get("content", "")
        print(f"小红书分析结果:\n{result[:500]}...")
        return result
    
    def analyze_heimao(self) -> str:
        """子Kimi3: 分析黑猫投诉"""
        print("\n" + "="*60)
        print("🔍 阶段2.3: Kimi3 分析黑猫投诉")
        print("="*60)
        
        complaints = self.collected_data["heimao_complaints"]
        if not complaints:
            return '{"error": "无黑猫投诉数据"}'
        
        complaint_texts = [c.get("text", "") for c in complaints]
        
        prompt = f"""你是一个专业的投诉分析师。

请分析以下黑猫投诉记录，要求：
1. 统计投诉类型分布（如质量问题、服务问题、虚假宣传等）
2. 找出最常见的投诉原因
3. 评估品牌对投诉的处理态度

黑猫投诉：
{chr(10).join([f"{i+1}. {text}" for i, text in enumerate(complaint_texts)])}

请输出JSON格式的分析结果：
{{
    "投诉总数": {len(complaints)},
    "投诉类型分布": {{
        "质量问题": N,
        "服务问题": N,
        "虚假宣传": N,
        "其他": N
    }},
    "主要投诉原因": ["原因1", "原因2"],
    "品牌处理态度": "积极/消极/一般",
    "总结": "一句话总结"
}}"""
        
        response = self.heimao_kimi.chat([
            {"role": "user", "content": prompt}
        ])
        
        result = response.get("content", "")
        print(f"黑猫投诉分析结果:\n{result[:500]}...")
        return result
    
    def generate_final_report(self, taobao_classify_result: str, taobao_content_result: str, xiaohongshu_analysis: str, heimao_analysis: str) -> str:
        """主控Kimi: 汇总分析结果"""
        print("\n" + "="*60)
        print("📝 阶段3: 主控Kimi生成最终报告")
        print("="*60)
        
        product_name = self.collected_data["product_name"] or "未知商品"
        
        prompt = f"""你是一个专业的商品口碑分析报告撰写师。

请根据以下数据源的分析结果，生成一份完整的商品口碑分析报告。

商品名称：{product_name}

=== 淘宝评论分类（反讽检测+LoRA分析）===
{taobao_classify_result}

=== 淘宝评论内容分析（Kimi分析）===
{taobao_content_result}

=== 小红书笔记分析 ===
{xiaohongshu_analysis}

=== 黑猫投诉分析 ===
{heimao_analysis}

请输出以下JSON格式的最终报告：
{{
    "商品信息": {{
        "商品名称": "{product_name}"
    }},
    "淘宝评论": {{
        "好评率": "X%",
        "差评率": "X%",
        "主要优点": ["优点1", "优点2"],
        "主要问题": ["问题1", "问题2"]
    }},
    "小红书": {{
        "总体评价": "正面/负面/中性",
        "避坑建议": ["建议1", "建议2"]
    }},
    "黑猫投诉": {{
        "投诉数量": N,
        "主要问题": ["问题1", "问题2"]
    }},
    "综合评分": "X/10",
    "购买建议": "建议购买/不建议购买/观望",
    "总结": "200字综合分析"
}}"""
        
        response = self.main_kimi.chat([
            {"role": "user", "content": prompt}
        ])
        
        return response.get("content", "分析完成")
    
    def run(self, tool_functions: dict, brand: str, product: str, driver):
        """运行完整的分析流程"""
        print("="*60)
        print("🚀 多Kimi协作商品分析系统")
        print("="*60)
        
        if self.tracker:
            self.tracker.record("系统", "start", {"brand": brand, "product": product}, "开始分析")
        
        # 阶段1: 主控Kimi收集数据
        if not self.collect_data(tool_functions, brand, product, driver):
            print("❌ 数据收集失败")
            return
        
        # 阶段2: 并行分析
        # 2.1 淘宝评论：分类(反讽+LoRA) + 内容分析(Kimi)
        taobao_classify_result = self.analyze_taobao_classify(tool_functions)
        taobao_content_result = self.analyze_taobao_content()
        
        # 2.2 小红书、黑猫
        xiaohongshu_result = self.analyze_xiaohongshu()
        heimao_result = self.analyze_heimao()
        
        # 阶段3: 主控Kimi生成最终报告
        final_report = self.generate_final_report(
            taobao_classify_result,
            taobao_content_result,
            xiaohongshu_result, 
            heimao_result
        )
        
        # 保存日志
        if self.tracker:
            self.tracker.print_summary()
            self.tracker.save()
        
        return final_report


def main():
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    profile_dir = r"C:\unified_bot_profile"
    
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        print("\n[1/3] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        print("\n[2/3] 打开小红书，请登录...")
        driver.get("https://www.xiaohongshu.com")
        input("  登录完成后，按回车继续...")
        
        print("\n[3/3] 打开黑猫投诉，请登录...")
        driver.get("https://tousu.sina.com.cn")
        input("  登录完成后，按回车继续...")
        
        mcp_server = MCPToolServer()
        
        tool_functions = {
            "search_product": lambda brand, product, max_results=5: 
                mcp_server.search_product(brand=brand, product=product, max_results=max_results, driver=driver),
            "get_comments": lambda url="", brand="", product="", max_count=100:
                mcp_server.get_comments(url=url, brand=brand, product=product, max_count=max_count, driver=driver),
            "search_xiaohongshu": lambda keyword, max_notes=50:
                mcp_server.search_xiaohongshu(keyword=keyword, max_notes=max_notes, driver=driver),
            "search_heimao": lambda brand, max_complaints=30:
                mcp_server.search_heimao(brand=brand, max_complaints=max_complaints, driver=driver),
            "detect_sarcasm": lambda texts, topics=None:
                mcp_server.detect_sarcasm(texts, topics or ["" for _ in texts]),
            "llm_judge_sarcasm": lambda text, topic:
                mcp_server.llm_judge_sarcasm(text, topic),
            "sentiment_analysis": lambda texts, category:
                mcp_server.sentiment_analysis(texts, category),
            "classify_category": lambda product_name:
                mcp_server.classify_category(product_name)
        }
        
        # 初始化追踪器
        tracker = ToolCallTracker()
        
        agent = MultiKimiAgent(tracker=tracker)
        result = agent.run(tool_functions, "虎邦", "鸡蛋酱", driver)
        
        print("\n" + "="*60)
        print("📊 最终分析报告")
        print("="*60)
        print(result)
        
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    main()
