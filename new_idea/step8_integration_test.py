# 08_integration_test.py
"""
Step 8: 集成测试
- 端到端测试：输入商品链接→品类判断→模型选择→分析输出
"""

from step7_router import analyze_comments


def test_flow():
    """测试完整流程"""
    # 模拟输入
    test_cases = [
        {
            "name": "iPhone 15 Pro Max",
            "comments": [
                "拍照效果很棒，运行流畅",
                "续航太差了，一天要充几次",
                "屏幕显示效果顶级",
                "性价比不高，不如安卓",
                "系统很流畅，生态完善",
            ]
        },
        {
            "name": "纯棉T恤",
            "comments": [
                "面料舒服，穿着透气",
                "洗了几次缩水了",
                "款式好看，质量一般",
                "性价比超高，会回购",
            ]
        },
    ]
    
    for case in test_cases:
        print(f"\n{'='*40}")
        print(f"商品: {case['name']}")
        result = analyze_comments(case['name'], case['comments'])
        print(f"品类: {result['category']}")
        print(f"好评率: {result['positive_rate']:.1%}")
        print(f"阴阳怪气: {result['sarcasm_count']}条")
        print(f"好评: {result['positive']}, 差评: {result['negative']}")


if __name__ == "__main__":
    # 先确保模型已训练
    # test_flow()
    print("请先完成 Step3-Step7 后运行此测试")
