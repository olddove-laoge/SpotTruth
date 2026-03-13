# test_lora_with_kimi.py
"""测试Kimi判断品类 + LoRA情感分析"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from mcp_test.kimi_client import KimiClient
from step6_mcp_tools import MCPToolServer


# 品类映射
CATEGORY_HINTS = {
    "book": "书、小说、教材、绘本、图书",
    "tablet": "平板、ipad、surface、平板电脑",
    "electronics": "手机、iphone、电脑、笔记本、电子产品",
    "fruit": "水果、苹果、橙子、芒果、草莓",
    "shampoo": "洗发水、护发素、洗头膏",
    "dairy": "牛奶、酸奶、奶酪、奶粉、乳制品",
    "clothing": "衣服、T恤、衬衫、裙子、裤子、外套",
    "water_heater": "热水器、电热水器、燃气热水器",
    "hotel": "酒店、民宿、宾馆、客栈、公寓"
}


def main():
    print("=" * 60)
    print("Kimi + LoRA 情感分析测试")
    print("=" * 60)
    
    # 1. 登录淘宝
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    profile_dir = r"C:\unified_bot_profile"
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        print("\n[1/4] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        # 2. 爬取评论
        print("\n[2/4] 爬取评论...")
        mcp_server = MCPToolServer()
        
        # 搜索商品
        products = mcp_server.search_product(brand="优形", product="鸡胸肉", max_results=3, driver=driver)
        if not products:
            print("未找到商品")
            return
        
        print(f"找到商品: {products[0]['name']}")
        
        # 获取评论
        comments = mcp_server.get_comments(
            url=products[0]['url'],
            max_count=200,
            driver=driver
        )
        
        if not comments:
            print("未获取到评论")
            return
        
        print(f"获取到 {len(comments)} 条评论")
        
        # 提取全部评论文本
        comment_texts = [c['text'] for c in comments]
        print(f"评论示例: {comment_texts[0][:50]}...")
        
        # 3. Kimi判断品类
        print("\n[3/4] Kimi判断品类...")
        kimi = KimiClient()
        
        category_prompt = f"""根据以下商品名称，判断应该使用哪个品类模型进行情感分析。
商品名称: {products[0]['name']}

可选品类: {', '.join(CATEGORY_HINTS.keys())}

请直接输出品类名称，不要输出其他内容。"""
        
        response = kimi.chat([
            {"role": "user", "content": category_prompt}
        ])
        
        # 解析品类 - chat返回dict，需要取content
        category_text = response.get("content", "") if isinstance(response, dict) else str(response)
        category = category_text.strip().lower()
        # 提取第一个匹配的品类
        for cat in CATEGORY_HINTS.keys():
            if cat in category:
                category = cat
                break
        
        print(f"Kimi判断品类: {category}")
        
        # 4. LoRA情感分析
        print("\n[4/4] LoRA情感分析...")
        
        results = mcp_server.sentiment_analysis(
            texts=comment_texts,
            category=category
        )
        
        # 统计结果
        positive_results = [r for r in results if r['sentiment'] == 'positive']
        negative_results = [r for r in results if r['sentiment'] == 'negative']
        
        positive = len(positive_results)
        negative = len(negative_results)
        
        print(f"\n情感分析结果 ({category}模型):")
        print(f"  正面: {positive}/{len(results)}")
        print(f"  负面: {negative}/{len(results)}")
        
        # 展示好评前10条
        print(f"\n好评示例 (前{min(10, len(positive_results))}条):")
        for i, r in enumerate(positive_results[:10]):
            print(f"  {i+1}. {r['text'][:50]}...")
        
        # 展示差评前10条
        print(f"\n差评示例 (前{min(10, len(negative_results))}条):")
        for i, r in enumerate(negative_results[:10]):
            print(f"  {i+1}. {r['text'][:50]}...")
        
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    main()
