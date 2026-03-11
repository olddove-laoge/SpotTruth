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
        print("\n[1/3] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        # 登录小红书
        print("\n[2/3] 打开小红书，请登录...")
        driver.get("https://www.xiaohongshu.com")
        input("  登录完成后，按回车继续...")
        
        print("\n[3/3] 初始化MCP服务器...")
        
        # 初始化MCP工具服务器（传入已登录的driver）
        mcp_server = MCPToolServer()
        
        # 包装工具函数，传入driver
        def wrapped_search_product(brand, product, max_results=5):
            return mcp_server.search_product(brand=brand, product=product, max_results=max_results, driver=driver)
        
        def wrapped_get_comments(url="", brand="", product="", max_count=100):
            return mcp_server.get_comments(url=url, brand=brand, product=product, max_count=max_count, driver=driver)
        
        def wrapped_search_xiaohongshu(keyword, max_notes=30):
            return mcp_server.search_xiaohongshu(keyword=keyword, max_notes=max_notes, driver=driver)
        
        def wrapped_search_heimao(brand, max_complaints=50):
            return mcp_server.search_heimao(brand=brand, max_complaints=max_complaints)
        
        # 初始化Kimi
        kimi = KimiClient()
        
        # 用户输入
        user_message = "帮我分析下苹果手机怎么样"
        
        print(f"\n用户: {user_message}")
        
        # 工具函数映射
        tool_functions = {
            "search_product": wrapped_search_product,
            "get_comments": wrapped_get_comments,
            "search_xiaohongshu": wrapped_search_xiaohongshu,
            "search_heimao": wrapped_search_heimao
        }
        
        # 系统提示
        system_prompt = """你是一个专业的商品分析助手"避雷真"。
你的任务是帮用户分析商品口碑，识别虚假好评和阴阳怪气评价。

工作流程：
1. 先搜索淘宝商品
2. 获取商品评论
3. 搜索小红书相关避雷笔记
4. 搜索黑猫投诉
5. 综合分析给出建议

注意：
- 直接选择第一个搜索结果
- 调用工具时要提供完整参数"""
        
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
