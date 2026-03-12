# test_taobao_scraper.py
"""测试淘宝爬虫"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time
import urllib.parse

def login_and_test():
    """登录后直接测试（不关闭浏览器）"""
    from step6_mcp_tools import MCPToolServer
    
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    profile_dir = r"C:\unified_bot_profile"
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        # 1. 打开淘宝，让用户登录
        print("\n[1/2] 打开淘宝，请登录...")
        driver.get("https://www.taobao.com")
        input("  登录完成后，按回车继续...")
        
        # 2. 直接搜索并获取HTML
        print("\n[2/2] 开始搜索...")
        keyword = "华为 手机"
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"https://s.taobao.com/search?page=1&q={encoded_keyword}&imgfile=&js=1&stats_click=search_radio_all%3A1&initiative_id=staobaoz_{time.strftime('%Y%m%d')}&ie=utf8"
        
        print(f"访问: {search_url}")
        driver.get(search_url)
        time.sleep(5)  # 等待页面加载
        
        # 保存页面HTML
        html_file = "taobao_search_result.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"HTML已保存到: {html_file}")
        
        # 尝试查找商品元素
        print("\n尝试查找商品元素...")
        
        # 尝试多种选择器
        selectors = [
            "[class*='doubleCardWrapperAdapt']",
            "[class*='CardV2']",
            ".item",
            "[data-spm]",
        ]
        
        for selector in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"  选择器 '{selector}': 找到 {len(items)} 个元素")
        
        # 获取商品元素
        items = driver.find_elements(By.CSS_SELECTOR, "[class*='doubleCard']")
        
        if not items:
            print("未找到商品元素!")
        else:
            print(f"\n找到 {len(items)} 个商品卡片")
            
            # 打印前6个商品的详细信息
            for idx, item in enumerate(items[:6]):
                print(f"\n{'='*60}")
                print(f"商品 {idx+1}")
                print("="*60)
                
                # 标题
                title_elems = item.find_elements(By.CSS_SELECTOR, "[class*='title--']")
                if title_elems:
                    print(f"标题: {title_elems[0].text[:60]}")
                
                # 价格
                price_int_elems = item.find_elements(By.CSS_SELECTOR, "[class*='priceInt']")
                price_float_elems = item.find_elements(By.CSS_SELECTOR, "[class*='priceFloat']")
                price = ""
                if price_int_elems:
                    price = price_int_elems[0].text
                if price_float_elems:
                    price += "." + price_float_elems[0].text
                print(f"价格: ¥{price}")
                
                # 销量
                sales_elems = item.find_elements(By.CSS_SELECTOR, "[class*='realSales']")
                if sales_elems:
                    print(f"销量: {sales_elems[0].text}")
                
                # 图片
                img_elems = item.find_elements(By.CSS_SELECTOR, "[class*='mainPic--']")
                if img_elems:
                    src = img_elems[0].get_attribute('src') or ""
                    print(f"图片URL: {src}")
                
                # 店铺名
                shop_name_elems = item.find_elements(By.CSS_SELECTOR, "[class*='shopNameText']")
                if shop_name_elems:
                    print(f"店铺名: {shop_name_elems[0].text}")
                
                # 店铺标签
                shop_tag_elems = item.find_elements(By.CSS_SELECTOR, "[class*='shopTagText']")
                if shop_tag_elems:
                    print(f"店铺标签: {shop_tag_elems[0].text}")
                
                # 商品ID
                item_id = item.get_attribute("data-spm-act-id")
                print(f"商品ID: {item_id}")
                
                # URL
                if item_id and item_id.isdigit():
                    print(f"商品URL: https://item.taobao.com/item.htm?id={item_id}")
    
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    print("=" * 50)
    print("淘宝爬虫测试")
    print("=" * 50)
    
    login_and_test()
