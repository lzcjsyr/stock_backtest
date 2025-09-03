"""
回测结果可视化模块
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class BacktestVisualizer:
    def __init__(self, results_df, output_dir="results/charts"):
        """
        初始化可视化器
        """
        self.results_df = results_df.copy()
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 数据预处理
        self.results_df['date'] = pd.to_datetime(self.results_df['date'])
        
    def plot_cumulative_returns(self):
        """绘制累计收益曲线"""
        plt.figure(figsize=(12, 8))
        
        # 主图：累计收益
        plt.subplot(2, 1, 1)
        plt.plot(self.results_df['date'], 
                self.results_df['cumulative_return'] * 100, 
                linewidth=2, color='#2E86AB', label='策略收益')
        
        plt.title('📈 低价股策略累计收益曲线', fontsize=16, fontweight='bold')
        plt.ylabel('累计收益率 (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 填充区域
        plt.fill_between(self.results_df['date'], 
                        0, 
                        self.results_df['cumulative_return'] * 100,
                        alpha=0.3, color='#2E86AB')
        
        # 子图：月度收益
        plt.subplot(2, 1, 2)
        colors = ['red' if x < 0 else 'green' for x in self.results_df['monthly_return']]
        plt.bar(self.results_df['date'], 
               self.results_df['monthly_return'] * 100,
               color=colors, alpha=0.7, width=20)
        
        plt.title('📊 月度收益率分布', fontsize=14, fontweight='bold')
        plt.ylabel('月收益率 (%)', fontsize=12)
        plt.xlabel('时间', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/cumulative_returns.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ 累计收益图已保存至 {self.output_dir}/cumulative_returns.png")
    
    def plot_risk_analysis(self):
        """绘制风险分析图"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 收益率分布直方图
        monthly_returns = self.results_df['monthly_return'] * 100
        ax1.hist(monthly_returns, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.axvline(monthly_returns.mean(), color='red', linestyle='--', 
                   label=f'平均收益: {monthly_returns.mean():.1f}%')
        ax1.set_title('🎯 月收益率分布', fontweight='bold')
        ax1.set_xlabel('月收益率 (%)')
        ax1.set_ylabel('频次')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 滚动最大回撤
        cumulative = self.results_df['cumulative_return']
        peak = cumulative.expanding().max()
        drawdown = (peak - cumulative) / (1 + peak) * 100
        
        ax2.fill_between(self.results_df['date'], 0, -drawdown, 
                        color='red', alpha=0.3, label='回撤区域')
        ax2.plot(self.results_df['date'], -drawdown, color='red', linewidth=2)
        ax2.set_title('📉 最大回撤分析', fontweight='bold')
        ax2.set_ylabel('回撤 (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 收益稳定性（滚动收益率）
        rolling_returns = self.results_df['monthly_return'].rolling(window=6).mean() * 100
        ax3.plot(self.results_df['date'], rolling_returns, 
                color='green', linewidth=2, label='6个月滚动平均收益')
        ax3.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax3.set_title('📈 收益稳定性分析', fontweight='bold')
        ax3.set_ylabel('滚动平均收益率 (%)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 年度收益对比
        self.results_df['year'] = self.results_df['date'].dt.year
        yearly_returns = self.results_df.groupby('year')['monthly_return'].apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        colors = ['red' if x < 0 else 'green' for x in yearly_returns]
        bars = ax4.bar(yearly_returns.index, yearly_returns, color=colors, alpha=0.7)
        ax4.set_title('📅 年度收益对比', fontweight='bold')
        ax4.set_ylabel('年收益率 (%)')
        ax4.set_xlabel('年份')
        ax4.grid(True, alpha=0.3)
        
        # 在柱子上添加数值标签
        for bar, value in zip(bars, yearly_returns):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{value:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/risk_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ 风险分析图已保存至 {self.output_dir}/risk_analysis.png")
    
    def generate_report(self):
        """生成文字报告"""
        monthly_returns = self.results_df['monthly_return']
        cumulative_returns = self.results_df['cumulative_return']
        
        # 计算关键指标
        total_return = cumulative_returns.iloc[-1] * 100
        annual_return = (1 + cumulative_returns.iloc[-1]) ** (12 / len(monthly_returns)) - 1
        annual_return = annual_return * 100
        
        volatility = monthly_returns.std() * np.sqrt(12) * 100
        max_drawdown = ((cumulative_returns.expanding().max() - cumulative_returns) / 
                       (1 + cumulative_returns.expanding().max())).max() * 100
        
        win_rate = (monthly_returns > 0).mean() * 100
        
        # 最佳和最差月份
        best_month = monthly_returns.max() * 100
        worst_month = monthly_returns.min() * 100
        
        report = f"""
📊 低价股策略回测报告
{'='*50}

📈 收益指标:
• 总收益率: {total_return:.2f}%
• 年化收益率: {annual_return:.2f}%
• 最佳单月: {best_month:.2f}%
• 最差单月: {worst_month:.2f}%

⚡ 风险指标:
• 年化波动率: {volatility:.2f}%
• 最大回撤: {max_drawdown:.2f}%
• 夏普比率: {(annual_return - 3) / volatility:.2f}
• 胜率: {win_rate:.1f}%

📅 回测期间:
• 开始时间: {self.results_df['date'].min().strftime('%Y-%m-%d')}
• 结束时间: {self.results_df['date'].max().strftime('%Y-%m-%d')}
• 总月数: {len(monthly_returns)}
"""
        
        # 保存报告
        with open(f'{self.output_dir}/backtest_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        print(f"✅ 详细报告已保存至 {self.output_dir}/backtest_report.txt")

if __name__ == "__main__":
    # 模拟数据测试
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='M')
    results_df = pd.DataFrame({
        'date': dates,
        'monthly_return': np.random.normal(0.01, 0.05, len(dates)),
        'cumulative_return': np.cumsum(np.random.normal(0.01, 0.05, len(dates)))
    })
    
    visualizer = BacktestVisualizer(results_df)
    print("✅ 可视化模块测试完成")