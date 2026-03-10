# test_all_scrapers.py
"""测试所有爬虫MCP工具"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options


def open_homepages():
    """打开三个平台首页，让用户确认登录状态"""
    print("\n" + "=" * 60)
    print("步骤1: 打开各平台首页，请确认登录状态")
    print("=" * 60)
    
    driver_path = r"E:\edgedriver_win64\msedgedriver.exe"
    
    # 使用统一的profile（所有平台共用登录状态）
    profile_dir = r"C:\unified_bot_profile"
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"user-data-dir={profile_dir}")
    
    driver = webdriver.Edge(service=Service(driver_path), options=options)
    
    try:
        # 1. 淘宝首页
        print("\n[1/3] 打开淘宝首页...")
        driver.get("https://www.taobao.com")
        input("  确认登录后，按回车继续...")
        
        # 2. 小红书首页
        print("\n[2/3] 打开小红书首页...")
        driver.get("https://www.xiaohongshu.com")
        input("  确认登录后，按回车继续...")
        
        # 3. 黑猫投诉首页
        print("\n[3/3] 打开黑猫投诉首页...")
        driver.get("https://tousu.sina.com.cn")
        input("  确认登录后，按回车继续...")
        
    finally:
        driver.quit()
        print("\n浏览器已关闭，开始测试...")


def test_taobao():
    """测试淘宝爬虫"""
    print("\n" + "=" * 50)
    print("测试1: 淘宝搜索")
    print("=" * 50)
    
    server = MCPToolServer()
    
    # 搜索商品
    products = server.search_product(brand="华为", product="手机", max_results=3)
    print(f"找到 {len(products)} 个商品:")
    for i, p in enumerate(products):
        print(f"  {i+1}. {p.get('name', 'N/A')[:50]}")
    
    return products


def test_xiaohongshu():
    """测试小红书爬虫"""
    print("\n" + "=" * 50)
    print("测试2: 小红书搜索")
    print("=" * 50)
    
    server = MCPToolServer()
    
    # 搜索笔记
    notes = server.search_xiaohongshu("华为手机", max_notes=10)
    print(f"找到 {len(notes)} 条笔记:")
    for i, n in enumerate(notes[:5]):
        print(f"  {i+1}. {n.get('text', 'N/A')[:60]}...")
    
    return notes


def test_heimao():
    """测试黑猫投诉爬虫"""
    print("\n" + "=" * 50)
    print("测试3: 黑猫投诉搜索")
    print("=" * 50)
    
    server = MCPToolServer()
    
    # 搜索投诉
    complaints = server.search_heimao("华为", max_complaints=10)
    print(f"找到 {len(complaints)} 条投诉:")
    for i, c in enumerate(complaints[:5]):
        print(f"  {i+1}. {c.get('text', 'N/A')[:60]}...")
    
    return complaints


if __name__ == "__main__":
    print("=" * 50)
    print("MCP爬虫工具测试")
    print("=" * 50)
    
    from step6_mcp_tools import MCPToolServer
    
    # 先打开首页确认登录
    open_homepages()
    
    # 测试淘宝
    test_taobao()
    
    # 测试小红书
    test_xiaohongshu()
    
    # 测试黑猫投诉
    test_heimao()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
