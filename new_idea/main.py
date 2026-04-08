#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""避雷真 - 新版入口

运行方式:
    python main.py

环境变量:
    KIMI_API_KEY: Kimi API密钥
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.core_agent import main as agent_main

if __name__ == "__main__":
    sys.exit(agent_main())
