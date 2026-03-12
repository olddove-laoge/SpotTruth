# test_taobao_agent.py
"""测试 Kimi + 真实淘宝爬虫 Agent"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from mcp_test.kimi_client import KimiClient
from step6_mcp_tools import MCPToolServer


# 工具定义
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
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_comments",
            "description": "【推荐】统一分析评论：自动进行讽刺检测+情感分析。流程：对所有评论先进行讽刺检测，是讽刺的用LLM判断，正常评论用LoRA模型分析，最后合并结果。只需要调用这一个工具就能完成所有分析",
            "parameters": {
                "type": "object",
                "properties": {
                    "comments": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "source": {"type": "string"}}, "description": "评论列表"}},
                    "category": {"type": "string", "description": "商品品类"},
                    "product_name": {"type": "string", "description": "商品名称（可选）"}
                },
                "required": ["comments", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_by_source",
            "description": "分析评论数据。流程：1)淘宝评论→讽刺检测→正常评论用LoRA分析，讽刺评论用LLM判断→得到淘宝好/差评率 2)小红书笔记和黑猫投诉直接返回文本列表（后续由Kimi分析）",
            "parameters": {
                "type": "object",
                "properties": {
                    "taobao_comments": {"type": "array", "items": {"type": "object"}, "description": "淘宝评论列表"},
                    "xiaohongshu_notes": {"type": "array", "items": {"type": "object"}, "description": "小红书笔记列表"},
                    "heimao_complaints": {"type": "array", "items": {"type": "object"}, "description": "黑猫投诉列表"},
                    "category": {"type": "string", "description": "商品品类"},
                    "product_name": {"type": "string", "description": "商品名称（可选）"}
                },
                "required": ["category"]
            }
        }
    }
]


def main():
    print("=" * 60)
    print("Kimi + 真实爬虫 Agent 测试")
    print("=" * 60)
    
    # 1. 先打开浏览器让用户登录
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    profile_dir = r"C:\unified_bot_profile"
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        # 登录淘宝
        print("\n[1/4] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        # 登录小红书
        print("\n[2/4] 打开小红书，请登录...")
        driver.get("https://www.xiaohongshu.com")
        input("  登录完成后，按回车继续...")
        
        # 登录黑猫投诉
        print("\n[3/4] 打开黑猫投诉，请登录...")
        driver.get("https://tousu.sina.com.cn")
        input("  登录完成后，按回车继续...")
        
        print("\n[4/4] 初始化MCP服务器...")
        
        # 初始化MCP工具服务器（传入已登录的driver）
        mcp_server = MCPToolServer()
        
        # 包装工具函数，传入driver
        def wrapped_search_product(brand, product, max_results=5):
            return mcp_server.search_product(brand=brand, product=product, max_results=max_results, driver=driver)
        
        def wrapped_get_comments(url="", brand="", product="", max_count=100):
            return mcp_server.get_comments(url=url, brand=brand, product=product, max_count=max_count, driver=driver)
        
        def wrapped_search_xiaohongshu(keyword, max_notes=50):
            return mcp_server.search_xiaohongshu(keyword=keyword, max_notes=max_notes, driver=driver)
        
        def wrapped_search_heimao(brand, max_complaints=30):
            return mcp_server.search_heimao(brand=brand, max_complaints=max_complaints, driver=driver)
        
        def wrapped_detect_sarcasm(texts, topics=None):
            topic_list = topics if topics else ["" for _ in texts]
            return mcp_server.detect_sarcasm(texts, topic_list)
        
        def wrapped_llm_judge_sarcasm(text, topic):
            return mcp_server.llm_judge_sarcasm(text, topic)
        
        def wrapped_sentiment_analysis(texts, category):
            return mcp_server.sentiment_analysis(texts, category)
        
        def wrapped_classify_category(product_name):
            return mcp_server.classify_category(product_name)
        
        def wrapped_analyze_comments(comments, category, product_name=""):
            return mcp_server.analyze_comments(comments, category, product_name)
        
        def wrapped_analyze_by_source(taobao_comments=None, xiaohongshu_notes=None, heimao_complaints=None, category="electronics", product_name=""):
            return mcp_server.analyze_by_source(taobao_comments, xiaohongshu_notes, heimao_complaints, category, product_name)
        
        # 初始化Kimi
        kimi = KimiClient()
        
        # 工具函数映射
        tool_functions = {
            "search_product": wrapped_search_product,
            "get_comments": wrapped_get_comments,
            "search_xiaohongshu": wrapped_search_xiaohongshu,
            "search_heimao": wrapped_search_heimao,
            "detect_sarcasm": wrapped_detect_sarcasm,
            "llm_judge_sarcasm": wrapped_llm_judge_sarcasm,
            "sentiment_analysis": wrapped_sentiment_analysis,
            "classify_category": wrapped_classify_category,
            "analyze_comments": wrapped_analyze_comments,
            "analyze_by_source": wrapped_analyze_by_source
        }
        
        # 用户输入
        user_message = "帮我分析下优形鸡胸肉怎么样"
        
        print(f"\n用户: {user_message}")
        
        # 系统提示
        system_prompt = """你是一个专业的商品分析助手"避雷真"。
你的任务是帮用户分析商品口碑，识别虚假好评和阴阳怪气评价。

【强制流程】（按顺序执行）：
1. 根据用户输入，判断商品的品牌名、商品名、商品品类
2. 搜索淘宝商品（search_product）
3. 获取淘宝商品评论（get_comments）
4. 搜索小红书相关避雷笔记（search_xiaohongshu）
5. 搜索黑猫投诉记录（search_heimao）
6. 判断商品品类（classify_category）

【关键步骤7】调用 analyze_by_source 工具
- 这个工具会：
  1. 对淘宝评论进行讽刺检测（TOSPrompt）
     - 正常评论 → 用LoRA模型分析情感
     - 讽刺评论 → 用LLM判断真实情感
     - 输出：淘宝好/差评率
  2. 小红书笔记和黑猫投诉直接返回文本列表

【后续步骤】你需要进行最终分析：
- 使用Kimi分析小红书笔记内容，给出分析结论
- 使用Kimi分析黑猫投诉内容，给出分析结论
- 结合淘宝好/差评率、小红书分析、黑猫投诉分析
- 生成完整的分析报告和购买建议

【输出格式】JSON格式：
```json
{
    "商品信息": {"品牌": "...", "商品": "...", "品类": "..."},
    "淘宝分析": {"好评率": 0.0, "差评率": 0.0, "讽刺数": N, "样本数": N},
    "小红书分析": "分析结论...",
    "黑猫投诉分析": "分析结论...",
    "总结": "完整分析报告",
    "购买建议": "建议购买/不建议购买/观望"
}
```"""

        print("\n开始对话...\n")
        
        # 调用Kimi
        result = kimi.chat_with_function(
            user_message=user_message,
            tools=TOOLS,
            tool_functions=tool_functions,
            system_prompt=system_prompt
        )
        
        print("\n" + "=" * 60)
        print("Kimi 最终回复:")
        print("=" * 60)
        print(result)
        
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    main()
