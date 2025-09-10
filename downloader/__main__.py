#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据管理模块入口

使用方式: python -m downloader
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from downloader.cli import main

if __name__ == "__main__":
    main()