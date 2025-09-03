"""
低价股投资策略实现
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar

class LowPriceStrategy:
    def __init__(self, min_price=2.0, top_n=50, initial_capital=100000):
        """
        初始化低价股策略
        
        Args:
            min_price: 最低价格筛选条件（默认2元）
            top_n: 选择股票数量（默认50只）
            initial_capital: 初始资金（默认10万）
        """
        self.min_price = min_price
        self.top_n = top_n
        self.initial_capital = initial_capital
        self.results = []
        
    def select_stocks(self, price_data, date):
        """
        根据策略选择股票
        """
        day_data = price_data[price_data['date'] == date].copy()
        
        if len(day_data) == 0:
            return pd.DataFrame()
        
        # 筛选价格大于min_price的股票
        filtered_data = day_data[day_data['close'] >= self.min_price].copy()
        
        # 按收盘价升序排列，选择最低价的top_n只股票
        selected = filtered_data.nsmallest(self.top_n, 'close')
        
        print(f"📅 {date}: 筛选出 {len(selected)} 只股票，价格区间 {selected['close'].min():.2f}-{selected['close'].max():.2f}元")
        
        return selected
    
    def calculate_monthly_return(self, buy_data, sell_data):
        """计算月度收益率"""
        if len(buy_data) == 0 or len(sell_data) == 0:
            return 0.0
        
        # 按股票代码匹配买卖数据
        merged = pd.merge(buy_data[['symbol', 'close']], 
                         sell_data[['symbol', 'close']], 
                         on='symbol', 
                         suffixes=('_buy', '_sell'))
        
        if len(merged) == 0:
            return 0.0
        
        # 计算每只股票的收益率
        merged['return'] = (merged['close_sell'] - merged['close_buy']) / merged['close_buy']
        
        # 等权重平均收益率
        monthly_return = merged['return'].mean()
        
        return monthly_return
    
    def run_backtest(self, price_data, start_date, end_date):
        """
        运行回测
        """
        print(f"🚀 开始回测: {start_date} 到 {end_date}")
        
        # 转换日期格式
        price_data['date'] = pd.to_datetime(price_data['date'])
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # 获取所有交易日
        trading_dates = price_data['date'].unique()
        trading_dates.sort()
        
        # 筛选回测期间的日期
        trading_dates = [d for d in trading_dates if start_date <= d <= end_date]
        
        # 按月分组
        monthly_dates = {}
        for date in trading_dates:
            month_key = (date.year, date.month)
            if month_key not in monthly_dates:
                monthly_dates[month_key] = date
        
        # 执行月度回测
        current_capital = self.initial_capital
        self.results = []
        
        monthly_dates_list = list(monthly_dates.values())
        
        for i in range(len(monthly_dates_list) - 1):
            buy_date = monthly_dates_list[i]
            sell_date = monthly_dates_list[i + 1]
            
            # 选择股票
            selected_stocks = self.select_stocks(price_data, buy_date.strftime('%Y-%m-%d'))
            
            if len(selected_stocks) == 0:
                continue
            
            # 获取卖出日期的价格
            sell_prices = price_data[price_data['date'] == sell_date.strftime('%Y-%m-%d')]
            
            # 计算月度收益
            monthly_return = self.calculate_monthly_return(selected_stocks, sell_prices)
            
            # 更新资金
            current_capital *= (1 + monthly_return)
            
            # 记录结果
            result = {
                'date': buy_date,
                'selected_stocks': len(selected_stocks),
                'monthly_return': monthly_return,
                'cumulative_capital': current_capital,
                'cumulative_return': (current_capital - self.initial_capital) / self.initial_capital
            }
            
            self.results.append(result)
            
            print(f"📈 {buy_date.strftime('%Y-%m')}: 收益率 {monthly_return:.2%}, 累计资金 {current_capital:.0f}")
        
        # 计算最终指标
        self.calculate_performance_metrics()
        
        return pd.DataFrame(self.results)
    
    def calculate_performance_metrics(self):
        """计算绩效指标"""
        if not self.results:
            return
        
        returns = [r['monthly_return'] for r in self.results]
        cumulative_returns = [r['cumulative_return'] for r in self.results]
        
        # 计算年化收益率
        total_months = len(returns)
        total_return = cumulative_returns[-1] if cumulative_returns else 0
        annual_return = (1 + total_return) ** (12 / total_months) - 1 if total_months > 0 else 0
        
        # 计算最大回撤
        peak = 0
        max_drawdown = 0
        for cum_ret in cumulative_returns:
            if cum_ret > peak:
                peak = cum_ret
            drawdown = (peak - cum_ret) / (1 + peak)
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算夏普比率（假设无风险利率为3%）
        excess_returns = [r - 0.03/12 for r in returns]
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(12) if np.std(excess_returns) != 0 else 0
        
        # 胜率
        win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0
        
        print("\n" + "="*50)
        print("📊 回测结果汇总")
        print("="*50)
        print(f"📈 年化收益率: {annual_return:.2%}")
        print(f"📉 最大回撤: {max_drawdown:.2%}")
        print(f"⚡ 夏普比率: {sharpe_ratio:.2f}")
        print(f"🎯 胜率: {win_rate:.2%}")
        print(f"📅 回测月数: {total_months}")
        print(f"💰 最终资金: {self.results[-1]['cumulative_capital']:.0f}")
        print("="*50)

if __name__ == "__main__":
    strategy = LowPriceStrategy(min_price=2.0, top_n=50)
    print("✅ 策略模块初始化完成")