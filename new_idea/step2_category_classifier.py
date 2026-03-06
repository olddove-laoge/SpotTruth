# 02_category_classifier.py
"""
Step 2: 商品品类判断模块
- 名称关键词匹配 + Kimi LLM兜底
"""

from openai import OpenAI
import json

# Kimi API配置
KIMI_API_KEY = "sk-NxnJvWVKw9cun9Y80gjfQp7PyWR9rOMwy9VH2aNU28xOdxcr"
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_MODEL = "moonshot-v1-8k"

CATEGORIES = ["book", "tablet", "phone", "fruit", "shampoo", "dairy", "clothing", "computer", "water_heater", "hotel"]

CATEGORY_KEYWORDS = {
    "book": ["书", "图书", "小说", "教材", "绘本"],
    "tablet": ["平板", "ipad", "平板电脑", "surface"],
    "phone": ["手机", "iphone", "安卓", "智能手机"],
    "fruit": ["水果", "苹果", "橙子", "芒果", "草莓", "荔枝"],
    "shampoo": ["洗发水", "护发素", "洗头膏", "洗发液"],
    "dairy": ["牛奶", "酸奶", "奶酪", "奶粉", "乳制品"],
    "clothing": ["衣服", "T恤", "衬衫", "裙子", "裤子", "外套", "服装"],
    "computer": ["电脑", "笔记本", "计算机", "laptop"],
    "water_heater": ["热水器", "电热水器", "燃气热水器"],
    "hotel": ["酒店", "民宿", "宾馆", "客栈", "公寓"],
}

# 初始化Kimi客户端
client = OpenAI(
    api_key=KIMI_API_KEY,
    base_url=KIMI_BASE_URL,
)


def classify_by_name(product_name: str) -> str:
    """通过商品名称判断品类"""
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in product_name for kw in keywords):
            return category
    return ""


def classify_by_llm(product_name: str, comments_sample: list) -> str:
    """Kimi LLM兜底判断品类"""
    if not comments_sample:
        comments_sample = ["无评论数据"]
    
    sample_text = "\n".join([f"- {c}" for c in comments_sample[:3]])
    
    prompt = f"""你是一个商品分类助手。根据商品名称和评论内容，判断该商品属于以下哪个类别：
可选类别：{', '.join(CATEGORIES)}

商品名称：{product_name}

评论示例：
{sample_text}

请直接回复商品类别名称，不要添加其他内容。如果无法判断，请回复"未知"。"""

    try:
        response = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        result = response.choices[0].message.content
        if result:
            result = result.strip()
        
        for cat in CATEGORIES:
            if cat in result:
                return cat
        
        return "未知"
    
    except Exception as e:
        print(f"Kimi API调用失败: {e}")
        return "未知"


def classify_category(product_name: str, comments: list) -> str:
    """主函数：品类判断"""
    # Step 1: 名称匹配
    result = classify_by_name(product_name)
    if result:
        return result
    
    # Step 2: LLM兜底
    llm_result = classify_by_llm(product_name, comments)
    if llm_result and llm_result != "未知":
        return llm_result
    
    return "未知"


if __name__ == "__main__":
    # 测试
    test_cases = [
        ("iPhone 15 Pro Max", ["拍照很棒", "续航太差了"]),
        ("纯棉T恤", ["面料舒服", "洗了缩水"]),
        ("戴尔笔记本电脑", ["运行流畅", "屏幕清晰"]),
    ]
    
    for name, comments in test_cases:
        result = classify_category(name, comments)
        print(f"{name} -> {result}")
