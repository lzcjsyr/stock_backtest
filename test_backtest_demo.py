"""
小市值轮动策略回测系统 - 演示脚本

展示如何使用小市值轮动策略回测系统的各种功能。

作者：Claude Code
"""

from small_cap_rotation_backtest import SmallCapRotationBacktest, run_small_cap_backtest
from datetime import datetime
import time

def demo_basic_usage():
    """演示基本使用方法"""
    print("🎯 演示1：基本使用方法")
    print("=" * 50)
    
    # 使用便捷函数
    result = run_small_cap_backtest(
        n_stocks=5,
        min_price=8.0,
        exclude_st=True,
        start_date='2025-06-01',
        end_date='2025-08-27',
        export_excel=True,
        plot_chart=True
    )
    
    print(f"📊 回测摘要:")
    summary = result['summary']
    print(f"  - 总收益率: {summary['total_return']:.2%}")
    print(f"  - 年化收益率: {summary['annualized_return']:.2%}")
    print(f"  - 最大回撤: {summary['max_drawdown']:.2%}")
    print(f"  - 夏普比率: {summary['sharpe_ratio']:.2f}")
    print(f"  - 期末价值: {summary['final_value']:,.0f}元")
    
    if 'excel_file' in result:
        print(f"📊 Excel文件: {result['excel_file']}")
    if 'chart_file' in result:
        print(f"📈 图表文件: {result['chart_file']}")

def demo_advanced_usage():
    """演示高级使用方法"""
    print("\n\n🎯 演示2：高级自定义参数")
    print("=" * 50)
    
    # 创建自定义回测实例
    backtest = SmallCapRotationBacktest(
        n_stocks=15,              # 选择15只股票
        min_price=3.0,            # 最低价格3元
        exclude_st=False,         # 包含ST股票
        start_date='2025-05-01',  # 开始日期
        end_date='2025-08-27',    # 结束日期
        initial_capital=200000    # 20万初始资金
    )
    
    print("📊 开始高级回测...")
    start_time = time.time()
    summary = backtest.run_backtest()
    end_time = time.time()
    
    print(f"⏱️  回测耗时: {end_time - start_time:.2f}秒")
    print(f"📊 高级回测结果:")
    print(f"  - 回测期数: {summary['total_periods']}")
    print(f"  - 总收益率: {summary['total_return']:.2%}")
    print(f"  - 年化收益率: {summary['annualized_return']:.2%}")
    print(f"  - 波动率: {summary['volatility']:.2%}")
    print(f"  - 夏普比率: {summary['sharpe_ratio']:.2f}")
    print(f"  - 最大回撤: {summary['max_drawdown']:.2%}")
    print(f"  - 期末净值: {summary['final_nav']:.4f}")
    print(f"  - 期末价值: {summary['final_value']:,.0f}元")
    
    # 导出详细报告
    excel_file = backtest.export_to_excel(f'detailed_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    chart_file = backtest.plot_nav_curve(f'detailed_nav_curve_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
    
    print(f"📊 详细Excel报告: {excel_file}")
    print(f"📈 净值曲线图: {chart_file}")

def demo_parameter_comparison():
    """演示参数对比测试"""
    print("\n\n🎯 演示3：参数对比测试")
    print("=" * 50)
    
    # 测试不同参数组合
    test_configs = [
        {"n_stocks": 5, "min_price": 10.0, "name": "保守策略(5只,10元+)"},
        {"n_stocks": 10, "min_price": 5.0, "name": "平衡策略(10只,5元+)"},
        {"n_stocks": 20, "min_price": 3.0, "name": "激进策略(20只,3元+)"}
    ]
    
    print("🏁 开始参数对比测试...")
    comparison_results = []
    
    for config in test_configs:
        print(f"\n📊 测试 {config['name']}")
        
        try:
            result = run_small_cap_backtest(
                n_stocks=config["n_stocks"],
                min_price=config["min_price"],
                exclude_st=True,
                start_date='2025-06-01',
                end_date='2025-08-27',
                export_excel=False,  # 不导出文件节省时间
                plot_chart=False
            )
            
            summary = result['summary']
            comparison_results.append({
                'strategy': config['name'],
                'total_return': summary['total_return'],
                'annualized_return': summary['annualized_return'],
                'sharpe_ratio': summary['sharpe_ratio'],
                'max_drawdown': summary['max_drawdown']
            })
            
            print(f"  ✅ 总收益: {summary['total_return']:.2%}")
            print(f"     年化收益: {summary['annualized_return']:.2%}")
            print(f"     夏普比率: {summary['sharpe_ratio']:.2f}")
            print(f"     最大回撤: {summary['max_drawdown']:.2%}")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            comparison_results.append({
                'strategy': config['name'],
                'error': str(e)
            })
    
    # 输出对比结果
    print(f"\n📋 参数对比汇总:")
    print("-" * 80)
    print(f"{'策略':<20} {'总收益':<10} {'年化收益':<10} {'夏普比率':<10} {'最大回撤':<10}")
    print("-" * 80)
    
    for result in comparison_results:
        if 'error' in result:
            print(f"{result['strategy']:<20} {'失败':<10}")
        else:
            print(f"{result['strategy']:<20} "
                  f"{result['total_return']:>8.1%} "
                  f"{result['annualized_return']:>9.1%} "
                  f"{result['sharpe_ratio']:>9.2f} "
                  f"{result['max_drawdown']:>9.1%}")

def main():
    """主演示函数"""
    print("🚀 小市值轮动策略回测系统 - 功能演示")
    print("=" * 60)
    print("本演示将展示如何使用小市值轮动策略回测系统")
    print("包括基本使用、高级配置和参数对比等功能")
    print()
    
    try:
        # 演示1：基本使用
        demo_basic_usage()
        
        # 演示2：高级使用
        demo_advanced_usage()
        
        # 演示3：参数对比
        demo_parameter_comparison()
        
        print(f"\n\n🎉 所有演示完成！")
        print("=" * 60)
        print("💡 使用提示：")
        print("1. 可以通过命令行直接运行：python small_cap_rotation_backtest.py --help")
        print("2. 也可以在Python代码中导入使用")
        print("3. 生成的Excel和PNG文件包含详细的回测结果")
        print("4. 支持多种参数组合，适应不同风险偏好")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()