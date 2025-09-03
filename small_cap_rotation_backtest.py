"""
小市值轮动策略回测系统

策略说明：
1. 选择上海和深圳主板企业（沪市600/601/603、深市000/001/002/003）
2. 每月末基于收盘价找出市值最小的N只股票（默认10只）
3. 股价必须高于N元（默认10元）
4. 可选择过滤ST股票
5. 每月轮换一次，每只股票买入100股
6. 使用前复权价格计算收益

输出：
- Excel回测报告（选股记录+月度收益率）
- 净值曲线PNG图片

作者：Claude Code
依赖：stock_database.py, pandas, matplotlib, openpyxl
"""

import sqlite3
import pandas as pd
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import logging
from calendar import monthrange
import warnings
import os
warnings.filterwarnings('ignore')

from stock_database import StockDatabase

# 配置中文字体和日志
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmallCapRotationBacktest:
    """
    小市值轮动策略回测类
    
    核心功能：
    1. 股票筛选：主板+市值+价格+ST过滤
    2. 月末轮换：每月重新选股
    3. 收益计算：基于前复权价格
    4. 报告生成：Excel表格+PNG图表
    """
    
    def __init__(self, n_stocks=10, min_price=10.0, exclude_st=True, 
                 start_date='2023-01-01', end_date=None, initial_capital=1000000):
        """
        初始化回测参数
        
        Parameters:
        -----------
        n_stocks : int
            每月选择的股票数量，默认10只
        min_price : float
            股价最低要求，默认10元
        exclude_st : bool
            是否排除ST股票，默认True
        start_date : str
            回测开始日期 'YYYY-MM-DD'
        end_date : str
            回测结束日期，默认今天
        initial_capital : float
            初始资金，默认100万元
        """
        self.n_stocks = n_stocks
        self.min_price = min_price
        self.exclude_st = exclude_st
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
        self.initial_capital = initial_capital
        
        # 数据库连接
        self.db = StockDatabase()
        
        # 结果存储
        self.portfolio_history = []  # 每月选股记录
        self.performance_data = []   # 业绩数据
        self.nav_data = []          # 净值数据
        
        # 结果文件管理
        self._setup_result_directory()
        
        logger.info(f"🎯 小市值轮动策略回测初始化")
        logger.info(f"   📅 回测期间: {self.start_date.date()} 到 {self.end_date.date()}")
        logger.info(f"   📊 选股数量: {n_stocks}只")
        logger.info(f"   💰 最低价格: {min_price}元")
        logger.info(f"   🚫 排除ST: {exclude_st}")
        logger.info(f"   💵 初始资金: {initial_capital:,.0f}元")
        logger.info(f"   📁 结果目录: {self.result_dir}")
    
    def _setup_result_directory(self):
        """
        设置结果文件目录结构
        
        创建目录结构:
        - result/
          - backtest_MMDDHHMI/
            - backtest_MMDDHHMI.xlsx
            - backtest_MMDDHHMI.png
        """
        # 创建主结果目录
        result_base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result')
        os.makedirs(result_base_dir, exist_ok=True)
        
        # 生成当前回测的时间戳文件名 (月日时分)
        timestamp = datetime.now().strftime('%m%d%H%M')
        self.backtest_name = f'backtest_{timestamp}'
        
        # 创建当前回测的专用子目录
        self.result_dir = os.path.join(result_base_dir, self.backtest_name)
        os.makedirs(self.result_dir, exist_ok=True)
        
        # 设置文件路径
        self.excel_path = os.path.join(self.result_dir, f'{self.backtest_name}.xlsx')
        self.chart_path = os.path.join(self.result_dir, f'{self.backtest_name}.png')
    
    def _is_main_board(self, stock_code):
        """
        判断是否为主板股票
        
        主板定义：
        - 沪市：600/601/603开头
        - 深市：000/001/002/003开头
        """
        if stock_code.startswith(('600', '601', '603')):  # 沪市主板
            return True
        elif stock_code.startswith(('000', '001', '002', '003')):  # 深市主板
            return True
        else:
            return False
    
    def _get_month_end_dates(self):
        """
        获取回测期间所有月末最后交易日
        
        Returns:
        --------
        list
            月末最后交易日期列表
        """
        month_ends = []
        current_date = self.start_date.replace(day=1)  # 从月初开始
        
        while current_date <= self.end_date:
            # 获取当月最后一天
            year = current_date.year
            month = current_date.month
            last_day = monthrange(year, month)[1]
            calendar_month_end = current_date.replace(day=last_day)
            
            # 如果日历月末超出回测范围，跳过
            if calendar_month_end > self.end_date:
                break
            
            # 从日历月末向前查找最后一个有股价数据的交易日
            actual_month_end = self._get_last_trading_day_before(calendar_month_end)
            
            if actual_month_end and actual_month_end >= self.start_date:
                month_ends.append(actual_month_end)
                logger.debug(f"📅 {year}年{month}月: 日历月末={calendar_month_end.strftime('%Y-%m-%d')} -> 交易日月末={actual_month_end.strftime('%Y-%m-%d')}")
            
            # 移动到下个月
            if month == 12:
                current_date = current_date.replace(year=year + 1, month=1)
            else:
                current_date = current_date.replace(month=month + 1)
        
        return month_ends
    
    def _get_last_trading_day_before(self, target_date):
        """
        获取指定日期之前(含当日)的最后一个交易日
        
        使用多个蓝筹股组合判断交易日，比单一股票更可靠：
        - 选择多个大盘蓝筹股（平安银行000001、万科A000002等）
        - 只有当大多数股票都有数据时才认为是交易日
        - 避免因个别股票停牌导致的误判
        
        Parameters:
        -----------
        target_date : datetime
            目标日期
            
        Returns:
        --------
        datetime or None
            最后交易日，如果没有找到则返回None
        """
        try:
            # 选择几个稳定的大盘蓝筹股作为交易日判断基准
            # 这些股票很少停牌，数据相对稳定
            benchmark_stocks = ['000001', '000002', '000027', '000006', '000026']  # 平安、万科等蓝筹股
            
            # 向前查找最多15个自然日（包含节假日）
            search_date = target_date
            conn = self.db.get_connection()
            try:
                for _ in range(15):
                    date_str = search_date.strftime('%Y-%m-%d')
                    
                    # 统计有多少只基准股票在该日期有数据
                    cursor = conn.cursor()
                    placeholders = ','.join(['%s'] * len(benchmark_stocks))
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM stock_daily_kline 
                        WHERE stock_code IN ({placeholders}) AND trade_date = %s
                    """, benchmark_stocks + [date_str])
                    
                    count = cursor.fetchone()[0]
                    cursor.close()
                    
                    # 如果大多数基准股票（>=60%）都有数据，认为是交易日
                    required_count = max(1, int(len(benchmark_stocks) * 0.6))
                    if count >= required_count:
                        logger.debug(f"✅ 找到交易日: {search_date.strftime('%Y-%m-%d')} ({count}/{len(benchmark_stocks)}只基准股有数据)")
                        return search_date
                    else:
                        logger.debug(f"⚪ {search_date.strftime('%Y-%m-%d')}: 仅{count}/{len(benchmark_stocks)}只基准股有数据，可能非交易日")
                    
                    # 向前推一天
                    search_date = search_date - timedelta(days=1)
            finally:
                conn.close()
            
            logger.warning(f"⚠️  无法找到 {target_date.strftime('%Y-%m-%d')} 之前15天内的交易日")
            return None
            
        except Exception as e:
            logger.error(f"查找最后交易日出错: {e}")
            # 出错时回退到简单的工作日逻辑
            search_date = target_date
            for _ in range(7):
                if search_date.weekday() < 5:  # Monday=0, Friday=4
                    return search_date
                search_date = search_date - timedelta(days=1)
            return target_date
    
    def _get_next_month_first_trade_date(self, month_end_date):
        """
        获取指定月末日期后下个月的第一个交易日
        
        Parameters:
        -----------
        month_end_date : datetime
            月末日期
            
        Returns:
        --------
        datetime or None
            下个月第一个交易日，如果不存在则返回None
        """
        conn = self.db.get_connection()
        if not conn:
            return None
        
        try:
            # 找到月末日期后的下一个交易日
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MIN(trade_date) as first_trade_date
                FROM stock_daily_kline 
                WHERE trade_date > %s
            """, (month_end_date.strftime('%Y-%m-%d'),))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return pd.to_datetime(result[0])
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取下月第一个交易日失败: {e}")
            if conn:
                conn.close()
            return None
    
    def _get_stock_data_on_date(self, target_date):
        """
        获取指定日期的股票数据（价格+市值）
        
        Parameters:
        -----------
        target_date : datetime
            目标日期
            
        Returns:
        --------
        DataFrame
            包含股票代码、价格、市值的数据框
        """
        conn = self.db.get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            target_str = target_date.strftime('%Y-%m-%d')
            
            # 第一步：找到目标日期当天或之前最近的交易日
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(trade_date) as latest_date
                FROM stock_daily_kline 
                WHERE trade_date <= %s
            """, (target_str,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                logger.warning(f"⚠️  {target_date.date()} 之前无交易数据")
                return pd.DataFrame()
            
            latest_trade_date = result[0]
            logger.info(f"📅 使用交易日期: {latest_trade_date}")
            
            # 第二步：获取该交易日的所有股票数据
            sql = """
            SELECT 
                k.stock_code,
                k.close_price,
                k.trade_date,
                b.stock_name,
                b.circulating_market_value,
                b.total_market_value
            FROM stock_daily_kline k
            JOIN stock_basic_info b ON k.stock_code = b.stock_code
            WHERE k.trade_date = %s 
            AND b.is_active = 1
            AND b.circulating_market_value IS NOT NULL
            AND b.circulating_market_value > 0
            """
            
            df = pd.read_sql(sql, conn, params=[latest_trade_date])
            
            if df.empty:
                logger.warning(f"⚠️  {target_date.date()} 无股票数据")
                return df
            
            # 过滤条件
            # 1. 主板股票
            df = df[df['stock_code'].apply(self._is_main_board)]
            
            # 2. 价格筛选
            df = df[df['close_price'] >= self.min_price]
            
            # 3. ST股票过滤
            if self.exclude_st:
                df = df[~df['stock_name'].str.contains('ST', na=False)]
            
            # 4. 市值数据可用
            df = df.dropna(subset=['circulating_market_value'])
            
            logger.info(f"📊 {target_date.date()} 筛选后股票数量: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"获取 {target_date.date()} 股票数据失败: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def _select_stocks(self, stock_data):
        """
        选择市值最小的N只股票
        
        Parameters:
        -----------
        stock_data : DataFrame
            股票数据
            
        Returns:
        --------
        DataFrame
            选中的股票数据
        """
        if len(stock_data) < self.n_stocks:
            logger.warning(f"⚠️  可选股票数量({len(stock_data)})少于目标数量({self.n_stocks})")
        
        # 按流通市值排序，选择最小的N只
        selected = stock_data.nsmallest(self.n_stocks, 'circulating_market_value')
        
        logger.info(f"✅ 选中 {len(selected)} 只股票")
        for _, stock in selected.iterrows():
            logger.info(f"   {stock['stock_code']} {stock['stock_name']} "
                       f"价格:{stock['close_price']:.2f} "
                       f"市值:{stock['circulating_market_value']:.1f}亿")
        
        return selected
    
    def _calculate_position_allocation(self, selected_stocks, buy_date):
        """
        计算股票仓位分配（平均分配资金）
        
        新逻辑：
        1. 将总资金平均分配到N只股票
        2. 计算每只股票的买入股数（100股的整数倍）
        3. 记录实际投入金额和剩余现金
        
        Parameters:
        -----------
        selected_stocks : DataFrame
            选中的股票数据
        buy_date : datetime
            买入日期
            
        Returns:
        --------
        DataFrame
            包含股票代码、买入价格、股数、投入金额的数据框
        """
        if selected_stocks.empty:
            return pd.DataFrame()
        
        stock_codes = selected_stocks['stock_code'].tolist()
        conn = self.db.get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            # 获取买入日的开盘价
            placeholders = ','.join(['%s'] * len(stock_codes))
            sql = f"""
            SELECT stock_code, open_price
            FROM stock_daily_kline
            WHERE stock_code IN ({placeholders})
            AND trade_date = %s
            """
            
            params = stock_codes + [buy_date.strftime('%Y-%m-%d')]
            buy_prices_df = pd.read_sql(sql, conn, params=params)
            conn.close()
            
            # 计算平均分配的资金
            per_stock_budget = self.initial_capital / len(selected_stocks)
            
            allocations = []
            total_invested = 0.0
            
            for _, stock in selected_stocks.iterrows():
                code = stock['stock_code']
                name = stock['stock_name']
                
                # 查找买入价格
                price_data = buy_prices_df[buy_prices_df['stock_code'] == code]
                if price_data.empty:
                    logger.warning(f"⚠️  {code} 无买入价格数据")
                    continue
                
                buy_price = price_data.iloc[0]['open_price']
                if buy_price <= 0:
                    logger.warning(f"⚠️  {code} 买入价格无效: {buy_price}")
                    continue
                
                # 计算可买入股数（100股的整数倍）
                max_shares = int(per_stock_budget / buy_price)
                actual_shares = (max_shares // 100) * 100  # 取100的整数倍
                
                if actual_shares < 100:
                    logger.warning(f"⚠️  {code} 资金不足买入100股（需要{buy_price * 100:.0f}元，预算{per_stock_budget:.0f}元）")
                    # 如果预算不足100股，至少买100股
                    actual_shares = 100
                
                actual_investment = actual_shares * buy_price
                total_invested += actual_investment
                
                allocations.append({
                    'stock_code': code,
                    'stock_name': name,
                    'buy_price': buy_price,
                    'shares': actual_shares,
                    'investment': actual_investment,
                    'budget_allocation': per_stock_budget
                })
                
                logger.debug(f"   {code} {name}: {buy_price:.2f}元 × {actual_shares}股 = {actual_investment:,.0f}元")
            
            allocation_df = pd.DataFrame(allocations)
            remaining_cash = self.initial_capital - total_invested
            utilization_rate = total_invested / self.initial_capital
            
            logger.info(f"💰 资金分配完成:")
            logger.info(f"   总投入: {total_invested:,.0f}元 ({utilization_rate:.1%})")
            logger.info(f"   剩余现金: {remaining_cash:,.0f}元")
            logger.info(f"   平均每股预算: {per_stock_budget:,.0f}元")
            
            return allocation_df
            
        except Exception as e:
            logger.error(f"计算仓位分配失败: {e}")
            if conn:
                conn.close()
            return pd.DataFrame()
    
    def _calculate_portfolio_return(self, previous_position_allocation, current_month_end):
        """
        计算组合收益率（基于实际投入金额加权）
        
        新逻辑：
        1. 基于上期的实际仓位分配（股数和投入金额）
        2. 计算当月末卖出的收益
        3. 按投入金额加权计算总收益率
        
        Parameters:
        -----------
        previous_position_allocation : DataFrame  
            上期的仓位分配数据（包含股数、买入价、投入金额）
        current_month_end : datetime
            当期月末日期（卖出日期）
            
        Returns:
        --------
        tuple
            (月度收益率, 绝对盈亏金额, 总投入金额)
        """
        if previous_position_allocation.empty:
            return 0.0, 0.0, 0.0
        
        previous_codes = previous_position_allocation['stock_code'].tolist()
        
        try:
            conn = self.db.get_connection()
            if not conn:
                return 0.0, 0.0, 0.0
            
            # 获取当月末交易日（卖出日）
            current_date_str = current_month_end.strftime('%Y-%m-%d')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(trade_date) as latest_date
                FROM stock_daily_kline 
                WHERE trade_date <= %s
            """, (current_date_str,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                logger.warning(f"⚠️  {current_month_end.date()} 之前无交易数据")
                conn.close()
                return 0.0, 0.0, 0.0
            
            sell_date = result[0]
            
            # 查询卖出价格（收盘价）
            placeholders = ','.join(['%s'] * len(previous_codes))
            sell_sql = f"""
            SELECT stock_code, close_price as sell_price
            FROM stock_daily_kline
            WHERE stock_code IN ({placeholders})
            AND trade_date = %s
            """
            
            sell_params = previous_codes + [sell_date]
            sell_prices = pd.read_sql(sell_sql, conn, params=sell_params)
            conn.close()
            
            # 计算加权收益
            total_profit = 0.0  # 总盈亏金额
            total_investment = 0.0  # 总投入金额
            valid_positions = 0
            
            logger.info(f"📅 卖出日期: {sell_date} (收盘价)")
            logger.info(f"📊 仓位收益明细:")
            
            for _, position in previous_position_allocation.iterrows():
                code = position['stock_code']
                name = position['stock_name']
                buy_price = position['buy_price']
                shares = position['shares']
                investment = position['investment']
                
                # 查找卖出价格
                sell_price_data = sell_prices[sell_prices['stock_code'] == code]
                
                if not sell_price_data.empty:
                    sell_price = sell_price_data.iloc[0]['sell_price']
                    
                    if sell_price > 0:  # 确保价格有效
                        # 计算该持仓的绝对盈亏
                        position_profit = (sell_price - buy_price) * shares
                        position_return = position_profit / investment
                        
                        total_profit += position_profit
                        total_investment += investment
                        valid_positions += 1
                        
                        logger.info(f"   {code} {name}: "
                                  f"买入{buy_price:.2f}×{shares}股({investment:,.0f}元) -> "
                                  f"卖出{sell_price:.2f} = "
                                  f"{position_profit:+,.0f}元 ({position_return:+.2%})")
                    else:
                        logger.warning(f"⚠️  {code} 卖出价格无效: {sell_price}")
                        total_investment += investment  # 仍计入总投入
                else:
                    logger.warning(f"⚠️  {code} 缺少卖出价格数据")
                    total_investment += investment  # 仍计入总投入
            
            if total_investment > 0:
                portfolio_return = total_profit / total_investment
                logger.info(f"💰 组合收益汇总:")
                logger.info(f"   总投入: {total_investment:,.0f}元")
                logger.info(f"   总盈亏: {total_profit:+,.0f}元")
                logger.info(f"   收益率: {portfolio_return:+.2%}")
                logger.info(f"   有效仓位: {valid_positions}/{len(previous_position_allocation)}")
                
                return portfolio_return, total_profit, total_investment
            else:
                logger.warning("⚠️  无法计算收益率（无有效投入金额）")
                return 0.0, 0.0, 0.0
                
        except Exception as e:
            logger.error(f"计算收益率失败: {e}")
            if conn:
                conn.close()
            return 0.0, 0.0, 0.0
    
    def run_backtest(self):
        """
        运行完整回测
        
        Returns:
        --------
        dict
            回测结果汇总
        """
        logger.info("🚀 开始运行小市值轮动策略回测")
        
        # 获取所有月末日期
        month_ends = self._get_month_end_dates()
        logger.info(f"📅 回测期间共 {len(month_ends)} 个月末调仓日")
        
        current_nav = 1.0  # 初始净值
        current_cash = self.initial_capital  # 当前现金
        previous_position_allocation = pd.DataFrame()  # 上期仓位分配
        
        for i, month_end in enumerate(month_ends):
            logger.info(f"\n📊 第{i+1}/{len(month_ends)}期 - {month_end.date()}")
            
            # 获取股票数据
            stock_data = self._get_stock_data_on_date(month_end)
            
            if stock_data.empty:
                logger.warning(f"⚠️  {month_end.date()} 无可用数据，跳过")
                continue
            
            # 选择股票
            selected_stocks = self._select_stocks(stock_data)
            
            # 计算收益和更新资金（从第二期开始）
            monthly_return = 0.0
            monthly_profit = 0.0
            total_investment = 0.0
            
            if i > 0 and not previous_position_allocation.empty:
                # 计算上期持仓的收益
                monthly_return, monthly_profit, total_investment = self._calculate_portfolio_return(
                    previous_position_allocation, month_end
                )
                
                # 更新净值和现金
                current_nav *= (1 + monthly_return)
                current_cash = current_nav * self.initial_capital  # 卖出后的总资金
                
                logger.info(f"💰 资金更新: 总资金={current_cash:,.0f}元, 净值={current_nav:.4f}")
            
            # 计算下期的仓位分配（如果不是最后一期）
            next_position_allocation = pd.DataFrame()
            if i < len(month_ends) - 1:  # 不是最后一期
                # 获取下期买入日期
                next_buy_date = self._get_next_month_first_trade_date(month_end)
                if next_buy_date:
                    # 基于当前总资金重新计算仓位分配
                    temp_backtest = SmallCapRotationBacktest(
                        n_stocks=self.n_stocks,
                        min_price=self.min_price,
                        exclude_st=self.exclude_st,
                        initial_capital=current_cash  # 使用当前总资金
                    )
                    next_position_allocation = temp_backtest._calculate_position_allocation(
                        selected_stocks, next_buy_date
                    )
                    logger.info(f"📊 下期仓位分配完成")
            
            # 记录结果
            portfolio_record = {
                'date': month_end,
                'period': i + 1,
                'selected_stocks': selected_stocks.copy(),
                'position_allocation': next_position_allocation.copy(),
                'monthly_return': monthly_return,
                'monthly_profit': monthly_profit,
                'total_investment': total_investment,
                'current_cash': current_cash,
                'cumulative_nav': current_nav
            }
            
            performance_record = {
                'date': month_end,
                'period': i + 1,
                'monthly_return': monthly_return,
                'cumulative_return': current_nav - 1,
                'nav': current_nav,
                'portfolio_value': current_cash
            }
            
            self.portfolio_history.append(portfolio_record)
            self.performance_data.append(performance_record)
            self.nav_data.append({'date': month_end, 'nav': current_nav})
            
            logger.info(f"💰 月度收益: {monthly_return:.2%}, 累计净值: {current_nav:.4f}")
            
            # 更新持仓分配
            previous_position_allocation = next_position_allocation.copy()
        
        # 计算汇总统计
        returns = [p['monthly_return'] for p in self.performance_data[1:]]  # 排除第一期
        total_return = current_nav - 1
        annualized_return = (current_nav ** (12 / max(len(returns), 1))) - 1
        volatility = np.std(returns) * np.sqrt(12) if returns else 0
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        max_drawdown = self._calculate_max_drawdown()
        
        summary = {
            'total_periods': len(month_ends),
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_nav': current_nav,
            'final_value': current_cash
        }
        
        logger.info(f"\n🎯 回测完成！")
        logger.info(f"   📊 总收益率: {total_return:.2%}")
        logger.info(f"   📈 年化收益率: {annualized_return:.2%}")
        logger.info(f"   📉 最大回撤: {max_drawdown:.2%}")
        logger.info(f"   📊 夏普比率: {sharpe_ratio:.2f}")
        logger.info(f"   💰 期末价值: {summary['final_value']:,.0f}元")
        
        return summary
    
    def _calculate_max_drawdown(self):
        """计算最大回撤"""
        if not self.nav_data:
            return 0.0
        
        navs = [d['nav'] for d in self.nav_data]
        peak = navs[0]
        max_dd = 0.0
        
        for nav in navs:
            if nav > peak:
                peak = nav
            drawdown = (peak - nav) / peak
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def export_to_excel(self, filename=None):
        """
        导出回测结果到Excel
        
        Parameters:
        -----------
        filename : str
            输出文件名，默认使用预设的路径
        """
        if not filename:
            filename = self.excel_path
        
        logger.info(f"📊 导出Excel报告: {filename}")
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                
                # 1. 策略概览
                summary_data = {
                    '参数': ['选股数量', '最低价格', '排除ST', '回测期间', '初始资金'],
                    '设置': [f'{self.n_stocks}只', f'{self.min_price}元', 
                           '是' if self.exclude_st else '否',
                           f'{self.start_date.date()} 到 {self.end_date.date()}',
                           f'{self.initial_capital:,.0f}元']
                }
                
                if self.performance_data:
                    final_data = self.performance_data[-1]
                    summary_data['参数'].extend([
                        '总收益率', '年化收益率', '最大回撤', '夏普比率', '期末净值'
                    ])
                    summary_data['设置'].extend([
                        f"{final_data['cumulative_return']:.2%}",
                        f"{((final_data['nav'] ** (12/len(self.performance_data))) - 1):.2%}",
                        f"{self._calculate_max_drawdown():.2%}",
                        "需计算",
                        f"{final_data['nav']:.4f}"
                    ])
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='策略概览', index=False)
                
                # 2. 月度业绩
                if self.performance_data:
                    perf_df = pd.DataFrame(self.performance_data)
                    perf_df['日期'] = perf_df['date'].dt.strftime('%Y-%m-%d')
                    perf_df['月度收益率'] = perf_df['monthly_return'].map(lambda x: f"{x:.2%}")
                    perf_df['累计收益率'] = perf_df['cumulative_return'].map(lambda x: f"{x:.2%}")
                    perf_df['净值'] = perf_df['nav'].map(lambda x: f"{x:.4f}")
                    perf_df['组合价值'] = perf_df['portfolio_value'].map(lambda x: f"{x:,.0f}")
                    
                    output_perf = perf_df[['日期', '月度收益率', '累计收益率', '净值', '组合价值']]
                    output_perf.to_excel(writer, sheet_name='月度业绩', index=False)
                
                # 3. 选股明细
                if self.portfolio_history:
                    all_selections = []
                    for record in self.portfolio_history:
                        date_str = record['date'].strftime('%Y-%m-%d')
                        for _, stock in record['selected_stocks'].iterrows():
                            all_selections.append({
                                '日期': date_str,
                                '期数': record['period'],
                                '股票代码': stock['stock_code'],
                                '股票名称': stock['stock_name'],
                                '选股时收盘价': f"{stock['close_price']:.2f}",
                                '流通市值': f"{stock['circulating_market_value']:.1f}亿",
                                '总市值': f"{stock.get('total_market_value', 0):.1f}亿"
                            })
                    
                    selection_df = pd.DataFrame(all_selections)
                    selection_df.to_excel(writer, sheet_name='选股明细', index=False)
                
                # 4. 仓位分配明细
                if self.portfolio_history:
                    all_positions = []
                    for record in self.portfolio_history:
                        if 'position_allocation' in record and not record['position_allocation'].empty:
                            date_str = record['date'].strftime('%Y-%m-%d')
                            for _, position in record['position_allocation'].iterrows():
                                all_positions.append({
                                    '调仓日期': date_str,
                                    '期数': record['period'],
                                    '股票代码': position['stock_code'],
                                    '股票名称': position['stock_name'],
                                    '买入价格': f"{position['buy_price']:.2f}",
                                    '买入股数': f"{position['shares']}股",
                                    '投入金额': f"{position['investment']:,.0f}元",
                                    '预算分配': f"{position['budget_allocation']:,.0f}元"
                                })
                    
                    if all_positions:
                        position_df = pd.DataFrame(all_positions)
                        position_df.to_excel(writer, sheet_name='仓位分配', index=False)
                
                # 5. 净值曲线数据
                if self.nav_data:
                    nav_df = pd.DataFrame(self.nav_data)
                    nav_df['日期'] = nav_df['date'].dt.strftime('%Y-%m-%d')
                    nav_df['净值'] = nav_df['nav'].map(lambda x: f"{x:.4f}")
                    nav_df[['日期', '净值']].to_excel(writer, sheet_name='净值数据', index=False)
            
            logger.info(f"✅ Excel报告导出成功: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"导出Excel失败: {e}")
            return None
    
    def plot_nav_curve(self, filename=None):
        """
        绘制净值曲线图
        
        Parameters:
        -----------
        filename : str
            输出文件名，默认使用预设的路径
        """
        if not filename:
            filename = self.chart_path
        
        logger.info(f"📈 绘制净值曲线: {filename}")
        
        if not self.nav_data:
            logger.error("❌ 无净值数据，无法绘图")
            return None
        
        try:
            # 准备数据
            dates = [d['date'] for d in self.nav_data]
            navs = [d['nav'] for d in self.nav_data]
            
            # 创建图表，使用现代化设计风格
            plt.style.use('seaborn-v0_8-whitegrid')  # 使用更现代的样式
            
            # 重新设置中文字体，确保在样式应用后生效
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans', 'WenQuanYi Micro Hei']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, ax = plt.subplots(figsize=(16, 10))
            fig.patch.set_facecolor('#FAFAFA')  # 浅灰色背景
            
            # 绘制净值曲线 - 使用渐变色和阴影
            ax.plot(dates, navs, linewidth=3, color='#1B5E20', 
                          label='策略净值', zorder=3)
            
            # 填充净值曲线下方区域
            ax.fill_between(dates, navs, 1.0, where=[n >= 1.0 for n in navs], 
                           color='#4CAF50', alpha=0.2, label='盈利区域')
            ax.fill_between(dates, navs, 1.0, where=[n < 1.0 for n in navs], 
                           color='#F44336', alpha=0.2, label='亏损区域')
            
            # 绘制基准线
            ax.axhline(y=1.0, color='#757575', linestyle='--', alpha=0.8, 
                      linewidth=2, label='基准线', zorder=2)
            
            # 设置标题 - 分层展示，更清晰
            st_filter = "排除ST" if self.exclude_st else "包含ST"
            fig.suptitle('小市值轮动策略 - 净值曲线分析', 
                        fontsize=26, fontweight='bold', y=0.95, color='#1A1A1A')
            
            # 子标题显示参数
            ax.text(0.5, 1.02, f'选股:{self.n_stocks}只 | 最低价格:{self.min_price}元 | {st_filter}', 
                   transform=ax.transAxes, ha='center', fontsize=16, 
                   color='#424242', weight='medium')
            
            # 日期范围
            ax.text(0.5, 0.98, f'回测期间: {self.start_date.date()} 到 {self.end_date.date()}', 
                   transform=ax.transAxes, ha='center', fontsize=14, 
                   color='#666666', style='italic')
            
            ax.set_xlabel('日期', fontsize=16, color='#1A1A1A', weight='medium', labelpad=15)
            ax.set_ylabel('净值', fontsize=16, color='#1A1A1A', weight='medium', labelpad=15)
            
            # 格式化日期轴
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', 
                    fontsize=13, color='#424242')
            
            # 自定义网格
            ax.grid(True, alpha=0.4, linestyle=':', linewidth=1, color='#BDBDBD')
            ax.set_axisbelow(True)
            
            # Y轴格式和样式
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}'))
            ax.tick_params(axis='y', labelsize=13, colors='#424242')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDBDBD')
            ax.spines['bottom'].set_color('#BDBDBD')
            
            # 添加统计信息 - 现代卡片式设计
            if len(navs) > 0:
                total_return = navs[-1] - 1
                max_nav = max(navs)
                min_nav = min(navs)
                max_drawdown = self._calculate_max_drawdown()
                
                # 创建统计信息卡片
                stats_box = dict(boxstyle='round,pad=1', facecolor='white', 
                               edgecolor='#E0E0E0', linewidth=1.5, alpha=0.95)
                
                # 收益信息
                return_color = '#4CAF50' if total_return >= 0 else '#F44336'
                stats_text1 = f'📈 总收益率\n{total_return:+.1%}'
                ax.text(0.02, 0.98, stats_text1, transform=ax.transAxes,
                       verticalalignment='top', horizontalalignment='left',
                       bbox=stats_box, fontsize=14, weight='bold', color=return_color)
                
                # 风险信息
                stats_text2 = f'📊 最大回撤\n{max_drawdown:.1%}'
                ax.text(0.02, 0.85, stats_text2, transform=ax.transAxes,
                       verticalalignment='top', horizontalalignment='left',
                       bbox=stats_box, fontsize=14, weight='bold', color='#FF9800')
                
                # 净值信息
                stats_text3 = f'🎯 净值范围\n{min_nav:.3f} - {max_nav:.3f}'
                ax.text(0.02, 0.72, stats_text3, transform=ax.transAxes,
                       verticalalignment='top', horizontalalignment='left',
                       bbox=stats_box, fontsize=14, weight='bold', color='#2196F3')
            
            # 现代化图例设计
            legend = ax.legend(loc='upper right', frameon=True, fancybox=True, 
                             shadow=False, fontsize=13, 
                             bbox_to_anchor=(0.98, 0.98))
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_edgecolor('#E0E0E0')
            legend.get_frame().set_linewidth(1)
            legend.get_frame().set_alpha(0.95)
            
            # 调整边距和布局
            ax.margins(x=0.01, y=0.05)
            plt.subplots_adjust(left=0.08, right=0.95, top=0.85, bottom=0.12)
            
            # 保存图片
            plt.savefig(filename, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"✅ 净值曲线图保存成功: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"绘制净值曲线失败: {e}")
            return None

# 便捷函数
def run_small_cap_backtest(n_stocks=10, min_price=10.0, exclude_st=True,
                          start_date='2023-01-01', end_date=None,
                          export_excel=True, plot_chart=True):
    """
    运行小市值轮动策略回测的便捷函数
    
    Parameters:
    -----------
    n_stocks : int
        每月选择股票数量
    min_price : float
        股价最低要求
    exclude_st : bool
        是否排除ST股票
    start_date : str
        回测开始日期
    end_date : str
        回测结束日期
    export_excel : bool
        是否导出Excel
    plot_chart : bool
        是否绘制图表
        
    Returns:
    --------
    dict
        回测结果和文件路径
    """
    # 创建回测实例
    backtest = SmallCapRotationBacktest(
        n_stocks=n_stocks,
        min_price=min_price, 
        exclude_st=exclude_st,
        start_date=start_date,
        end_date=end_date
    )
    
    # 运行回测
    summary = backtest.run_backtest()
    
    result = {'summary': summary}
    
    # 导出Excel
    if export_excel:
        excel_file = backtest.export_to_excel()
        result['excel_file'] = excel_file
    
    # 绘制图表
    if plot_chart:
        chart_file = backtest.plot_nav_curve()
        result['chart_file'] = chart_file
    
    return result

# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="小市值轮动策略回测系统 - 核心策略参数配置",
        epilog="""
策略参数说明:
  --stocks N      选择N只最小市值股票 (建议: 5-20只, 影响分散度和收益)
  --min-price P   股价门槛P元以上 (建议: 3-15元, 过滤低价垃圾股)
  --include-st    包含ST风险股票 (默认排除, 风险偏好者可开启)
  
回测周期配置:
  --start DATE    回测开始日期 (格式: YYYY-MM-DD, 建议至少6个月)
  --end DATE      回测结束日期 (默认今日, 建议完整月度周期)
  
输出控制:
  --no-excel      跳过Excel详细报告 (加速测试时使用)
  --no-chart      跳过净值曲线图表 (批量测试时使用)

使用示例:
  python small_cap_rotation_backtest.py --stocks 8 --min-price 5.0 --start 2025-01-01
  python small_cap_rotation_backtest.py --include-st --stocks 15 --min-price 3.0
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # ================== 📊 策略参数配置区域 (直接修改这里的值) ==================
    # 🎯 核心策略参数 (影响收益表现)
    STOCKS_COUNT = 30        # 选股数量 (建议: 5-20只, 影响分散度和收益)
    MIN_PRICE = 2.0          # 最低股价 (建议: 3-15元, 过滤低价垃圾股) 
    INCLUDE_ST = True       # 包含ST股票 (True=包含风险股, False=排除ST)
    
    # 📅 回测周期参数 (影响测试范围)  
    START_DATE = '2021-01-01'  # 回测开始日期 (格式: YYYY-MM-DD, 建议至少6个月)
    END_DATE = '2025-08-27'    # 回测结束日期 (None=今日, 建议完整月度周期)
    
    # 💾 输出控制参数 (影响结果展示)
    EXPORT_EXCEL = True      # 导出Excel报告 (True=导出详细报告, False=跳过)
    PLOT_CHART = True        # 绘制净值图表 (True=生成图表, False=跳过)
    # ============================================================================
    
    # 核心策略参数
    strategy_group = parser.add_argument_group('策略核心参数 (影响收益表现)')
    strategy_group.add_argument("--stocks", type=int, default=STOCKS_COUNT, 
                              help=f"选股数量 (当前: {STOCKS_COUNT}只, 建议5-20只)")
    strategy_group.add_argument("--min-price", type=float, default=MIN_PRICE, 
                              help=f"最低股价 (当前: {MIN_PRICE}元, 建议3-15元)")
    strategy_group.add_argument("--include-st", action="store_true", default=INCLUDE_ST,
                              help=f"包含ST股票 (当前: {'包含' if INCLUDE_ST else '排除'}, 开启增加风险)")
    
    # 回测周期参数  
    period_group = parser.add_argument_group('回测周期参数 (影响测试范围)')
    period_group.add_argument("--start", default=START_DATE, 
                            help=f"开始日期 (当前: {START_DATE})")
    period_group.add_argument("--end", default=END_DATE, 
                            help=f"结束日期 (当前: {END_DATE or '今日'})")
    
    # 输出控制参数
    output_group = parser.add_argument_group('输出控制参数 (影响结果展示)')
    output_group.add_argument("--no-excel", action="store_true", default=not EXPORT_EXCEL,
                            help=f"不导出Excel报告 (当前: {'导出' if EXPORT_EXCEL else '跳过'})")
    output_group.add_argument("--no-chart", action="store_true", default=not PLOT_CHART,
                            help=f"不绘制净值图表 (当前: {'绘制' if PLOT_CHART else '跳过'})")
    
    args = parser.parse_args()
    
    # 如果没有命令行参数，使用代码中的常量设置
    if len(sys.argv) == 1:  # 只有脚本名，没有其他参数
        actual_stocks = STOCKS_COUNT
        actual_min_price = MIN_PRICE
        actual_include_st = INCLUDE_ST
        actual_start = START_DATE
        actual_end = END_DATE
        actual_export_excel = EXPORT_EXCEL
        actual_plot_chart = PLOT_CHART
        print(f"📋 使用代码配置参数:")
        print(f"   选股数量: {actual_stocks}只")
        print(f"   最低价格: {actual_min_price}元")
        print(f"   包含ST: {'是' if actual_include_st else '否'}")
        print(f"   回测期间: {actual_start} 到 {actual_end}")
        print(f"   导出Excel: {'是' if actual_export_excel else '否'}")
        print(f"   绘制图表: {'是' if actual_plot_chart else '否'}")
    else:
        # 使用命令行参数
        actual_stocks = args.stocks
        actual_min_price = args.min_price
        actual_include_st = args.include_st
        actual_start = args.start
        actual_end = args.end
        actual_export_excel = not args.no_excel
        actual_plot_chart = not args.no_chart
    
    # 参数验证提示
    if actual_stocks < 3:
        print("⚠️  警告: 选股数量过少(<3), 可能导致风险集中")
    if actual_stocks > 30:
        print("⚠️  警告: 选股数量过多(>30), 可能稀释小市值效应")
    if actual_min_price < 2.0:
        print("⚠️  警告: 最低价格过低(<2元), 退市风险较高")
    if actual_include_st:
        print("⚠️  警告: 已开启ST股票, 请注意风险控制")
    
    # 运行回测
    result = run_small_cap_backtest(
        n_stocks=actual_stocks,
        min_price=actual_min_price,
        exclude_st=not actual_include_st,
        start_date=actual_start,
        end_date=actual_end,
        export_excel=actual_export_excel,
        plot_chart=actual_plot_chart
    )
    
    print(f"\n🎉 回测完成！")
    if 'excel_file' in result:
        print(f"📊 Excel报告: {result['excel_file']}")
    if 'chart_file' in result:
        print(f"📈 净值图表: {result['chart_file']}")