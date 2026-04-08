#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""避雷真 - 快速启动脚本"""

import sys
import os

# 添加项目路径（确保能正确导入）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """快速启动入口"""
    # 检查环境变量
    if not os.getenv("KIMI_API_KEY"):
        print("❌ 错误: 未设置 KIMI_API_KEY 环境变量")
        print("请先设置环境变量:")
        print("  Windows CMD: set KIMI_API_KEY=your_api_key")
        print("  PowerShell:  $env:KIMI_API_KEY=\"your_api_key\"")
        print("  Linux/Mac:   export KIMI_API_KEY=your_api_key")
        return 1

    # 检查驱动路径
    from config import paths
    if not os.path.exists(paths.driver_path):
        print(f"❌ 错误: 找不到Edge驱动: {paths.driver_path}")
        print("请修改 config.py 中的 driver_path 为您本地的路径")
        return 1

    # 启动
    from agent import BileizhenAgent, AgentBuilder, create_driver

    driver = create_driver()
    try:
        agent = AgentBuilder().with_driver(driver).build()
        agent.run()
    finally:
        driver.quit()

    return 0

if __name__ == "__main__":
    sys.exit(main())
