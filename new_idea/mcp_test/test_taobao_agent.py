# test_taobao_agent.py
"""测试 Kimi + 真实淘宝爬虫 Agent"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    }
]


def main():
    print("=" * 60)
    print("Kimi + 真实淘宝爬虫 Agent 测试")
    print("=" * 60)
    
    # 初始化MCP工具服务器
    print("\n初始化MCP工具服务器...")
    mcp_server = MCPToolServer()
    print("MCP服务器初始化完成")
    
    # 初始化Kimi客户端
    kimi = KimiClient()
    
    # 用户输入
    user_message = "帮我分析下华为手机怎么样"
    
    print(f"\n用户: {user_message}")
    
    # 工具函数映射 - 使用真实MCP工具
    tool_functions = {
        "search_product": mcp_server.search_product,
        "get_comments": mcp_server.get_comments
    }
    
    # 系统提示
    system_prompt = """你是一个专业的商品分析助手"避雷真"。
你的任务是帮用户分析商品口碑，识别虚假好评和阴阳怪气评价。

工作流程：
1. 当用户要分析某个商品时，先搜索相关商品
2. 如果有多个搜索结果，默认选择第一个（无需询问用户）
3. 获取商品评论
4. 分析评论中的虚假好评和阴阳怪气
5. 给出综合评价和购买建议

注意：
- 直接选择第一个搜索结果，无需询问用户
- 调用工具时要提供完整参数
- 分析要客观真实"""
    
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


if __name__ == "__main__":
    main()
