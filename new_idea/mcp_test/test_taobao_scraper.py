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
        
        # 2. 传入已登录的driver给MCP工具
        print("\n[2/2] 开始搜索...")
        server = MCPToolServer()
        products = server.search_product(brand="华为", product="手机", max_results=3, driver=driver)
        
        print(f"\n找到 {len(products)} 个商品:")
        for i, p in enumerate(products):
            print(f"  {i+1}. {p.get('name', 'N/A')[:50]}")
            print(f"     价格: {p.get('price', 'N/A')} | 店铺: {p.get('shop', 'N/A')[:30]}")
            
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    print("=" * 50)
    print("淘宝爬虫测试")
    print("=" * 50)
    
    login_and_test()
