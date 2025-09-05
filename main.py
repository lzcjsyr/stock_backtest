#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from data_downloader import DataRouter

def print_banner():
    """打印程序横幅"""
    print("=" * 60)
    print("📈 股票回测系统")
    print("=" * 60)
    print("多资产类别数据管理与策略回测系统")
    print("支持A股、港股、美股、基金等多种资产")
    print("=" * 60)

def show_main_menu():
    """显示主菜单"""
    print("\n🎯 主菜单")
    print("1. 📡 数据管理 (多资产类别)")
    print("2. 📊 策略回测")
    print("3. ❌ 退出系统")
    return input("\n请选择功能 (1-3): ").strip()


def show_strategy_menu():
    """显示策略回测菜单"""
    strategies_dir = "strategies"
    strategies = []
    
    if os.path.exists(strategies_dir):
        strategies = [f[:-3] for f in os.listdir(strategies_dir) 
                     if f.endswith('.py') and not f.startswith('__')]
    
    print("\n📊 策略回测")
    if not strategies:
        print("❌ 当前没有可用的策略文件")
        input("按回车键返回主菜单...")
        return None
    
    print("可用策略:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    print(f"{len(strategies) + 1}. 返回主菜单")
    
    try:
        choice = int(input(f"\n请选择策略 (1-{len(strategies) + 1}): ").strip())
        if 1 <= choice <= len(strategies):
            return strategies[choice - 1]
        elif choice == len(strategies) + 1:
            return None
        else:
            print("❌ 无效选择")
            return None
    except ValueError:
        print("❌ 请输入有效数字")
        return None

def execute_with_error_handling(func, error_msg):
    """执行函数并处理错误"""
    try:
        func()
    except ImportError:
        print("❌ 数据下载模块导入失败，请检查模块是否正确安装")
    except Exception as e:
        print(f"❌ {error_msg}: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键继续...")

def run_backtest(strategy_name):
    """运行策略回测"""
    def _run():
        print(f"\n🚀 正在运行 {strategy_name} 策略回测...")
        
        strategy_module = __import__(f'strategies.{strategy_name}', fromlist=[strategy_name])
        
        if hasattr(strategy_module, 'run_backtest'):
            strategy_module.run_backtest()
            print(f"✅ {strategy_name} 策略回测完成！")
            print("📁 结果已保存到 results 文件夹")
        else:
            print(f"❌ 策略 {strategy_name} 缺少 run_backtest 函数")
    
    execute_with_error_handling(_run, "策略回测失败")

def main():
    """主函数"""
    print_banner()
    
    # 创建数据路由器
    data_router = DataRouter()
    
    while True:
        try:
            choice = show_main_menu()
            
            if choice == "1":
                # 数据管理 - 进入资产路由
                data_router.start()
            
            elif choice == "2":
                # 策略回测
                strategy = show_strategy_menu()
                if strategy:
                    run_backtest(strategy)
            
            elif choice == "3":
                print("\n👋 感谢使用股票回测系统！")
                break
            
            else:
                print("❌ 无效选择，请重新选择")
                input("按回车键继续...")
        
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，程序退出")
            break
        except Exception as e:
            print(f"\n❌ 程序异常: {e}")
            input("按回车键继续...")

if __name__ == "__main__":
    main()