# test_heimao_scraper.py
"""测试黑猫投诉爬虫"""

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
        # 1. 打开黑猫，让用户登录
        print("\n[1/2] 打开黑猫投诉，请登录...")
        driver.get("https://tousu.sina.com.cn")
        input("  登录完成后，按回车继续...")
        
        # 2. 直接在同一浏览器中搜索
        print("\n[2/2] 开始搜索...")
        server = MCPToolServer()
        complaints = server.search_heimao("华为", max_complaints=10)
        
        print(f"\n找到 {len(complaints)} 条投诉:")
        for i, c in enumerate(complaints[:5]):
            print(f"  {i+1}. {c.get('text', 'N/A')[:60]}...")
            
    finally:
        driver.quit()
        print("\n测试完成")


if __name__ == "__main__":
    print("=" * 50)
    print("黑猫投诉爬虫测试")
    print("=" * 50)
    
    login_and_test()
