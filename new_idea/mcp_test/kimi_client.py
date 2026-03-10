# kimi_client.py
"""Kimi API 客户端 - 支持 function calling"""

import json
from openai import OpenAI
from typing import List, Dict, Any, Optional


class KimiClient:
    """Kimi API 客户端"""
    
    def __init__(
        self, 
        api_key: str = "sk-NxnJvWVKw9cun9Y80gjfQp7PyWR9rOMwy9VH2aNU28xOdxcr",
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "moonshot-v1-8k"
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def chat(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7
    ) -> Dict:
        """调用Kimi API
        
        Args:
            messages: 对话历史
            tools: 工具定义列表
            temperature: 温度参数
            
        Returns:
            Dict: 包含回复内容和可能需要调用的工具
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if tools:
            params["tools"] = tools
        
        response = self.client.chat.completions.create(**params)
        
        result = {
            "content": response.choices[0].message.content,
            "tool_calls": []
        }
        
        # 检查是否需要调用工具
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                result["tool_calls"].append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                })
        
        return result
    
    def chat_with_function(
        self, 
        user_message: str,
        tools: List[Dict],
        tool_functions: Dict,
        system_prompt: str = "你是一个专业的商品分析助手，帮助用户分析商品口碑。",
        max_turns: int = 5
    ) -> str:
        """与工具一起使用的对话
        
        Args:
            user_message: 用户消息
            tools: 工具定义列表
            tool_functions: 工具函数映射 {"函数名": 函数对象}
            system_prompt: 系统提示
            max_turns: 最大对话轮次
            
        Returns:
            str: 最终回复
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        for turn in range(max_turns):
            # 调用Kimi
            response = self.chat(messages, tools=tools)
            
            # 检查是否需要调用工具
            if response["tool_calls"]:
                tool_call = response["tool_calls"][0]  # 取第一个
                func_name = tool_call["name"]
                func_args = tool_call["arguments"]
                
                print(f"\n[调用工具] {func_name}")
                print(f"   参数: {func_args}")
                
                # 添加助手的消息（包含tool call）
                assistant_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{turn}",
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": func_args if isinstance(func_args, str) else json.dumps(func_args)
                            }
                        }
                    ]
                }
                messages.append(assistant_msg)
                
                # 调用工具函数
                if func_name in tool_functions:
                    try:
                        # 解析参数
                        args = json.loads(func_args) if isinstance(func_args, str) else func_args
                        
                        # 调用函数
                        tool_result = tool_functions[func_name](**args)
                        print(f"   结果: {str(tool_result)[:200]}...")
                        
                        # 添加工具结果到对话
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}",
                            "content": str(tool_result)
                        })
                    except Exception as e:
                        print(f"   ❌ 工具调用失败: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": f"call_{turn}",
                            "content": f"错误: {str(e)}"
                        })
                else:
                    print(f"   ❌ 未找到函数: {func_name}")
            else:
                # 没有工具调用，返回结果
                if response["content"]:
                    return response["content"]
                break
        
        # 获取最终回复
        final_response = self.chat(messages, tools=None)
        return final_response["content"] if final_response["content"] else "分析完成"


if __name__ == "__main__":
    # 测试
    client = KimiClient()
    response = client.chat([
        {"role": "user", "content": "你好"}
    ])
    print(response)
