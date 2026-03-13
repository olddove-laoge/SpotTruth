# test_sentiment_lora.py
"""测试LoRA情感分析模型"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from step6_mcp_tools import MCPToolServer


def main():
    print("=" * 60)
    print("LoRA情感分析模型测试")
    print("=" * 60)
    
    server = MCPToolServer()
    
    # 测试各品类
    test_cases = [
        {"text": "东西质量很好，物流也快，满意！", "category": "electronics"},
        {"text": "这本书写得很有意思，推荐阅读", "category": "book"},
        {"text": "手机续航太差了，一天要充几次电", "category": "tablet"},
        {"text": "水果很新鲜，甜度高", "category": "fruit"},
        {"text": "洗发水很好用，控油效果明显", "category": "shampoo"},
        {"text": "牛奶口感不错，价格也实惠", "category": "dairy"},
        {"text": "衣服面料舒服，穿着很合身", "category": "clothing"},
        {"text": "热水器加热很快，洗澡很方便", "category": "water_heater"},
        {"text": "酒店位置好，服务态度也不错", "category": "hotel"},
    ]
    
    print("\n开始测试...\n")
    
    for i, case in enumerate(test_cases):
        print(f"[{i+1}/9] 测试 {case['category']} 品类")
        print(f"    文本: {case['text']}")
        
        try:
            results = server.sentiment_analysis(
                texts=[case['text']],
                category=case['category']
            )
            if results:
                r = results[0]
                print(f"    结果: {r['sentiment']} (置信度: {r['confidence']:.2%})")
            else:
                print(f"    结果: 模型加载失败")
        except Exception as e:
            print(f"    错误: {e}")
        print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
