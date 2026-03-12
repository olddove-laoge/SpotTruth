# test_kimi_tool_tracker.py
"""Kimi 工具调用追踪测试 - 记录每次工具调用"""

import sys
import os
import json
import time
from datetime import datetime

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
            "name": "analyze_by_source",
            "description": "分析评论数据",
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


class ToolCallTracker:
    """工具调用追踪器"""
    
    def __init__(self, log_file: str = None):
        self.calls = []
        self.start_time = None
        self.log_file = log_file
        
    def record_call(self, tool_name: str, arguments: dict, result_preview: str = None):
        """记录一次工具调用"""
        call_record = {
            "index": len(self.calls) + 1,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "tool_name": tool_name,
            "arguments": arguments,
            "result_preview": result_preview
        }
        self.calls.append(call_record)
        self._print_call(call_record)
        
    def _print_call(self, call_record: dict):
        """打印调用记录"""
        print(f"\n{'='*60}")
        print(f"🔧 工具调用 #{call_record['index']}: {call_record['tool_name']}")
        print(f"   时间: {call_record['timestamp']}")
        print(f"   参数: {json.dumps(call_record['arguments'], ensure_ascii=False, indent=4)}")
        if call_record['result_preview']:
            print(f"   结果预览: {call_record['result_preview'][:200]}...")
        print(f"{'='*60}\n")
        
    def save(self):
        """保存记录到文件"""
        if not self.log_file:
            self.log_file = f"tool_calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "start_time": self.start_time,
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_calls": len(self.calls),
                "calls": self.calls
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📝 工具调用记录已保存到: {self.log_file}")
        
    def print_summary(self):
        """打印汇总"""
        print(f"\n{'='*60}")
        print(f"📊 工具调用汇总")
        print(f"{'='*60}")
        print(f"总调用次数: {len(self.calls)}")
        
        tool_counts = {}
        for call in self.calls:
            tool_name = call['tool_name']
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            
        print(f"\n各工具调用次数:")
        for tool_name, count in tool_counts.items():
            print(f"  - {tool_name}: {count} 次")
        
        missing_tools = ['analyze_by_source']
        called_tools = set(tool_counts.keys())
        
        print(f"\n⚠️  未调用的关键工具:")
        for tool in missing_tools:
            if tool not in called_tools:
                print(f"  ❌ {tool}")
        print(f"{'='*60}\n")


def main():
    print("=" * 60)
    print("Kimi 工具调用追踪测试")
    print("=" * 60)
    
    # 初始化追踪器
    tracker = ToolCallTracker()
    tracker.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 启动浏览器
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
        
        mcp_server = MCPToolServer()
        
        # 包装工具函数，添加追踪
        def wrapped_search_product(brand, product, max_results=5):
            result = mcp_server.search_product(brand=brand, product=product, max_results=max_results, driver=driver)
            tracker.record_call("search_product", {"brand": brand, "product": product, "max_results": max_results}, str(result)[:200])
            return result
        
        def wrapped_get_comments(url="", brand="", product="", max_count=100):
            result = mcp_server.get_comments(url=url, brand=brand, product=product, max_count=max_count, driver=driver)
            tracker.record_call("get_comments", {"url": url, "brand": brand, "product": product, "max_count": max_count}, str(len(result)) + " 条评论")
            return result
        
        def wrapped_search_xiaohongshu(keyword, max_notes=50):
            result = mcp_server.search_xiaohongshu(keyword=keyword, max_notes=max_notes, driver=driver)
            tracker.record_call("search_xiaohongshu", {"keyword": keyword, "max_notes": max_notes}, str(len(result)) + " 条笔记")
            return result
        
        def wrapped_search_heimao(brand, max_complaints=30):
            result = mcp_server.search_heimao(brand=brand, max_complaints=max_complaints, driver=driver)
            tracker.record_call("search_heimao", {"brand": brand, "max_complaints": max_complaints}, str(len(result)) + " 条投诉")
            return result
        
        def wrapped_classify_category(product_name):
            result = mcp_server.classify_category(product_name)
            tracker.record_call("classify_category", {"product_name": product_name}, str(result))
            return result
        
        def wrapped_analyze_by_source(taobao_comments=None, xiaohongshu_notes=None, heimao_complaints=None, category="electronics", product_name=""):
            result = mcp_server.analyze_by_source(taobao_comments, xiaohongshu_notes, heimao_complaints, category, product_name)
            tracker.record_call("analyze_by_source", {
                "taobao_comments_count": len(taobao_comments) if taobao_comments else 0,
                "xiaohongshu_notes_count": len(xiaohongshu_notes) if xiaohongshu_notes else 0,
                "heimao_complaints_count": len(heimao_complaints) if heimao_complaints else 0,
                "category": category,
                "product_name": product_name
            }, str(result)[:200] if result else "None")
            return result
        
        tool_functions = {
            "search_product": wrapped_search_product,
            "get_comments": wrapped_get_comments,
            "search_xiaohongshu": wrapped_search_xiaohongshu,
            "search_heimao": wrapped_search_heimao,
            "classify_category": wrapped_classify_category,
            "analyze_by_source": wrapped_analyze_by_source
        }
        
        # 简化版 prompt
        system_prompt = """你是一个专业的商品分析助手。
用户说"帮我分析下优形鸡胸肉怎么样"。

请按顺序执行以下步骤：
1. 搜索淘宝商品（search_product，品牌"优形"，商品"鸡胸肉"）
2. 获取淘宝评论（get_comments）
3. 搜索小红书（search_xiaohongshu，关键词"优形鸡胸肉"）
4. 搜索黑猫投诉（search_heimao，品牌"优形"）
5. 判断商品品类（classify_category）
6. 【必须】调用 analyze_by_source 工具进行分析

完成所有步骤后，输出完整的分析报告。"""
        
        kimi = KimiClient()
        
        user_message = "帮我分析下优形鸡胸肉怎么样"
        print(f"\n用户: {user_message}")
        print("\n开始对话...\n")
        
        result = kimi.chat_with_function(
            user_message=user_message,
            tools=TOOLS,
            tool_functions=tool_functions,
            system_prompt=system_prompt,
            max_turns=10
        )
        
        # 打印汇总
        tracker.print_summary()
        
        # 保存记录
        tracker.save()
        
        print("\n" + "=" * 60)
        print("Kimi 最终回复:")
        print("=" * 60)
        print(result)
        
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    main()
