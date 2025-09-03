"""
主程序 - 低价股策略回测系统
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_fetcher import DataFetcher
from src.database import StockDatabase
from src.strategy import LowPriceStrategy
from src.visualizer import BacktestVisualizer

import pandas as pd
from datetime import datetime

def main():
    """主函数：执行完整的回测流程"""
    print("🚀 欢迎使用低价股策略回测系统！")
    print("📋 系统功能：")
    print("   1️⃣ 获取A股数据 (AKShare)")
    print("   2️⃣ 存储到本地数据库 (SQLite)")
    print("   3️⃣ 执行低价股策略回测")
    print("   4️⃣ 生成可视化分析报告")
    print("-" * 50)
    
    # 配置参数
    START_DATE = "2020-01-01"
    END_DATE = "2023-12-31"
    MIN_PRICE = 2.0      # 最低股价筛选
    TOP_N = 50          # 选择股票数量
    INITIAL_CAPITAL = 100000  # 初始资金10万
    
    try:
        # 步骤1：初始化组件
        print("\n🔧 初始化系统组件...")
        fetcher = DataFetcher()
        db = StockDatabase()
        strategy = LowPriceStrategy(min_price=MIN_PRICE, top_n=TOP_N, initial_capital=INITIAL_CAPITAL)
        
        # 步骤2：检查数据状态
        print("\n📊 检查数据库状态...")
        db_info = db.get_available_dates()
        
        if db_info is None or db_info['total_records'] == 0:
            print("📥 数据库为空，开始获取数据...")
            
            # 获取股票列表
            stock_list = fetcher.get_stock_list()
            if stock_list is None:
                print("❌ 获取股票列表失败，程序退出")
                return
            
            # 保存股票列表
            db.save_stock_list(stock_list)
            
            # 批量获取价格数据（演示用前100只股票）
            print("⚠️ 注意：为节省时间，演示版本仅获取前100只股票")
            sample_symbols = stock_list['code'].head(100).tolist()
            
            print(f"🔄 开始获取 {len(sample_symbols)} 只股票的历史数据...")
            price_data = fetcher.batch_fetch_data(sample_symbols, START_DATE, END_DATE)
            
            if len(price_data) > 0:
                db.save_stock_prices(price_data)
                print("✅ 数据获取和存储完成！")
            else:
                print("❌ 未获取到价格数据，程序退出")
                return
        else:
            print(f"✅ 数据库已有数据：{db_info['start_date']} ~ {db_info['end_date']}")
            print(f"📊 总记录数：{db_info['total_records']}")
        
        # 步骤3：执行回测
        print("\n🎯 开始执行低价股策略回测...")
        
        # 从数据库获取数据
        price_data = db.get_stock_price_range(START_DATE, END_DATE)
        print(f"📈 加载了 {len(price_data)} 条价格记录")
        
        if len(price_data) == 0:
            print("❌ 没有找到指定时间范围的数据")
            return
        
        # 运行策略回测
        results_df = strategy.run_backtest(price_data, START_DATE, END_DATE)
        
        if len(results_df) == 0:
            print("❌ 回测未产生结果")
            return
        
        # 步骤4：生成结果分析
        print("\n📊 生成可视化分析...")
        visualizer = BacktestVisualizer(results_df)
        
        # 生成图表
        print("🎨 正在生成累计收益图...")
        visualizer.plot_cumulative_returns()
        
        print("🎨 正在生成风险分析图...")
        visualizer.plot_risk_analysis()
        
        # 生成文字报告
        print("📝 正在生成分析报告...")
        visualizer.generate_report()
        
        # 保存回测结果
        results_file = 'results/backtest_results.csv'
        results_df.to_csv(results_file, index=False, encoding='utf-8-sig')
        
        print("\n🎉 回测完成！")
        print("📁 结果文件：")
        print(f"   • 详细数据：{results_file}")
        print(f"   • 图表文件：results/charts/")
        print(f"   • 分析报告：results/charts/backtest_report.txt")
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

def quick_demo():
    """快速演示模式"""
    print("⚡ 快速演示模式")
    print("📝 本模式将使用模拟数据展示系统功能")
    
    # 创建模拟回测结果
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='M')
    np_returns = [0.02, -0.03, 0.05, 0.01, -0.02, 0.04, 0.03, -0.01, 0.06, -0.04,
                  0.02, 0.03, 0.01, -0.02, 0.05, 0.02, -0.01, 0.03, 0.04, -0.03,
                  0.01, 0.02, -0.01, 0.04, 0.03, -0.02, 0.01, 0.05, -0.03, 0.02,
                  0.01, -0.01, 0.03, 0.02, -0.02, 0.04, 0.01, -0.01, 0.02, 0.03,
                  -0.01, 0.02, 0.01, 0.03, -0.02, 0.01, 0.02, 0.01]
    
    # 计算累计收益
    cumulative_returns = []
    cumulative = 0
    for ret in np_returns:
        cumulative = (1 + cumulative) * (1 + ret) - 1
        cumulative_returns.append(cumulative)
    
    results_df = pd.DataFrame({
        'date': dates[:len(np_returns)],
        'monthly_return': np_returns,
        'cumulative_return': cumulative_returns,
        'selected_stocks': [50] * len(np_returns),
        'cumulative_capital': [(1 + cr) * 100000 for cr in cumulative_returns]
    })
    
    print(f"📊 模拟数据生成完成，共 {len(results_df)} 个月的数据")
    
    # 生成可视化
    visualizer = BacktestVisualizer(results_df)
    visualizer.plot_cumulative_returns()
    visualizer.generate_report()
    
    print("✅ 演示完成！这就是系统的核心功能。")

if __name__ == "__main__":
    print("🎯 请选择运行模式：")
    print("1 - 完整回测（获取真实数据）")
    print("2 - 快速演示（使用模拟数据）")
    
    try:
        choice = input("\n请输入选择 (1/2): ").strip()
        
        if choice == "1":
            main()
        elif choice == "2":
            quick_demo()
        else:
            print("❌ 无效选择，启动快速演示模式")
            quick_demo()
            
    except KeyboardInterrupt:
        print("\n👋 用户取消，程序退出")
    except Exception as e:
        print(f"❌ 程序异常: {e}")