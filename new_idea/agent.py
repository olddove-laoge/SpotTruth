# agent.py
"""避雷真Agent - 商品口碑分析Agent（LLM驱动版）"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
            "description": "统一计算好评率/差评率，接收讽刺检测和情感分析的结果，输出统计报告",
            "parameters": {
                "type": "object",
                "properties": {
                    "sarcasm_results": {"type": "array", "description": "讽刺检测结果列表"},
                    "sentiment_results": {"type": "array", "description": "情感分析结果列表"}
                },
                "required": ["sarcasm_results", "sentiment_results"]
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
        
        # 对话历史
        self.conversation_history = []
        
        # 当前正在分析的商品
        self.current_product = ""
        
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
        """获取系统提示词 - 告诉LLM它应该怎么做"""
        
        # 构建已分析商品的摘要
        products_summary = ""
        if self.collected_products:
            products_summary = "\n已分析的商品的简要信息：\n"
            for name, data in self.collected_products.items():
                taobao = data.get("taobao_result", {})
                summary = f"- {name}: 好评率{taobao.get('好评率', 'N/A')}, 差评率{taobao.get('差评率', 'N/A')}"
                if data.get("xiaohongshu_result"):
                    summary += ", 小红书有分析"
                if data.get("heimao_result"):
                    summary += ", 黑猫投诉有分析"
                products_summary += summary + "\n"
        
        return f"""你是"避雷真"，一个专业的商品口碑分析助手。

## 你的核心能力
1. 分析淘宝商品的好评率/差评率
2. 识别虚假好评和阴阳怪气评价（反讽检测）
3. 搜索小红书避雷笔记
4. 搜索黑猫投诉记录
5. 提供购买建议

## 可用的工具
- search_product: 搜索淘宝商品
- get_comments: 获取淘宝商品评论
- search_xiaohongshu: 搜索小红书笔记
- search_heimao: 搜索黑猫投诉
- detect_sarcasm: 反讽检测模型
- sentiment_analysis: LoRA情感分析模型
- classify_category: 判断商品品类
- llm_judge_sarcasm: LLM判断反讽评论的真实情感

## 你应该怎么做

### 场景1: 用户要分析一个商品
1. 先用search_product搜索商品（如果没有商品链接）
2. 用get_comments获取评论
3. 用classify_category判断商品品类
4. 用detect_sarcasm检测反讽评论
5. 对反讽评论用llm_judge_sarcasm判断真实情感
6. 对正常评论用sentiment_analysis做情感分析
7. 计算好评率/差评率，返回分析结果

### 场景2: 询问用户是否需要小红书/黑猫
- 你应该友好地询问用户是否需要，然后根据用户回答决定是否调用工具

### 场景3: 用户追问之前分析过的商品
- 从已分析商品中读取结果，给出回答
- 如果用户想要更详细的信息，可以调用更多工具深入分析

### 场景4: 用户想要对比多个商品
- 读取已分析商品的结果，进行对比

## 重要规则
1. 你可以自主决定调用哪些工具，不需要每次都问用户
2. 分析完一个商品后，要把结果保存到上下文中（我会自动保存）
3. 用户没有明确说要分析新商品时，默认是询问之前分析过的商品{products_summary}
4. 如果用户只是闲聊，可以简单回答并引导到商品分析功能

## 输出格式
- 直接回复用户，不要输出工具调用过程
- 用友好、专业的语气回复
- 如果需要用户确认某些事情（如是否需要小红书），明确提问"""
    
    def save_product_result(self, product_name: str, result_data: dict):
        """保存商品分析结果"""
        self.collected_products[product_name] = result_data
        
        # 保存到文件作为备份
        cache_file = os.path.join(os.path.dirname(__file__), "data", "product_cache.json")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.collected_products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   [警告] 保存缓存失败: {e}")
    
    def load_product_cache(self):
        """加载商品缓存"""
        cache_file = os.path.join(os.path.dirname(__file__), "data", "product_cache.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.collected_products = json.load(f)
                print(f"\n📂 已加载 {len(self.collected_products)} 个已分析商品的缓存")
            except Exception as e:
                print(f"   [警告] 加载缓存失败: {e}")
    
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
        for turn in range(15):  # 最多15轮工具调用
            response = self.kimi.chat(messages, tools=TOOLS)
            
            if response.get("tool_calls"):
                tool_call = response["tool_calls"][0]
                func_name = tool_call["name"]
                func_args = json.loads(tool_call["arguments"]) if isinstance(tool_call["arguments"], str) else tool_call["arguments"]
                
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
                        
                        # 如果没有明确指定商品，默认选第一个
                        if result and not self.current_product:
                            self.current_product = result[0].get("name", "")
                            self.collected_products[self.current_product] = {
                                "brand": func_args.get("brand", ""),
                                "product": func_args.get("product", ""),
                                "product_info": result[0]
                            }
                        
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
                        result = self.mcp_server.sentiment_analysis(
                            texts=func_args.get("texts", []),
                            category=func_args.get("category", "electronics")
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
                        sarcasm_results = func_args.get("sarcasm_results", [])
                        sentiment_results = func_args.get("sentiment_results", [])
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
                        if self.current_product:
                            self.collected_products[self.current_product]["xiaohongshu_notes"] = result
                            
                    elif func_name == "search_heimao":
                        result = self.mcp_server.search_heimao(
                            brand=func_args.get("brand", ""),
                            max_complaints=func_args.get("max_complaints", 10),
                            driver=self.driver
                        )
                        if self.current_product:
                            self.collected_products[self.current_product]["heimao_complaints"] = result
                            
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
                    messages.append({
                        "role": "tool",
                        "tool_call_id": f"call_{turn}",
                        "content": f"成功: {str(result)[:500]}"
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
            else:
                # LLM直接回复，不调用工具
                content = response.get("content", "")
                
                # 保存对话历史
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": content})
                
                return content
        
        return "抱歉，我需要更多时间来思考这个问题。请稍后再试。"
    
    def run(self):
        """运行Agent"""
        self.welcome()
        
        # 加载之前的缓存
        self.load_product_cache()
        
        print("\n👤 您: ", end="")
        
        while True:
            try:
                user_input = input().strip()
                
                if not user_input:
                    print("\n👤 您: ", end="")
                    continue
                
                if user_input.lower() in ["quit", "退出", "q"]:
                    print("\n👋 再见！\n")
                    break
                
                # LLM自主处理
                response = self.recognize_intent_and_act(user_input)
                
                print(f"\n🤖 避雷真: {response}")
                print("\n👤 您: ", end="")
                
            except KeyboardInterrupt:
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
