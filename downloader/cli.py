#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .router import DataRouter

def print_banner():
    """打印程序横幅"""
    print("📡 股票数据管理系统")
    print("=" * 30)

def main():
    """数据管理CLI主函数"""
    print_banner()
    
    try:
        # 创建数据路由器并直接启动
        data_router = DataRouter()
        data_router.start()
    
    except KeyboardInterrupt:
        print("\n👋 感谢使用数据管理系统！")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()