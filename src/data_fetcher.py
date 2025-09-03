"""
数据获取模块 - 使用AKShare获取股票数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
from tqdm import tqdm

class DataFetcher:
    def __init__(self):
        """初始化数据获取器"""
        self.stock_list = None
        
    def get_stock_list(self):
        """获取A股股票列表"""
        print("📡 正在获取A股股票列表...")
        try:
            self.stock_list = ak.stock_info_a_code_name()
            print(f"✅ 成功获取 {len(self.stock_list)} 只股票信息")
            return self.stock_list
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return None
    
    def get_stock_price(self, symbol, start_date, end_date):
        """获取单只股票的历史价格数据"""
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol, 
                period="daily",
                start_date=start_date.replace('-', ''), 
                end_date=end_date.replace('-', ''),
                adjust=""
            )
            
            if df is not None and len(df) > 0:
                # 标准化列名
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open', 
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume'
                })
                df['symbol'] = symbol
                return df
                
        except Exception as e:
            print(f"⚠️ 获取 {symbol} 数据失败: {e}")
            return None
    
    def batch_fetch_data(self, symbols, start_date, end_date):
        """批量获取多只股票数据"""
        print(f"🔄 开始批量获取 {len(symbols)} 只股票数据...")
        
        all_data = []
        failed_count = 0
        
        for symbol in tqdm(symbols, desc="获取股票数据"):
            data = self.get_stock_price(symbol, start_date, end_date)
            if data is not None:
                all_data.append(data)
            else:
                failed_count += 1
            
            # 防止请求过快被限制
            time.sleep(0.1)
        
        print(f"✅ 成功获取 {len(all_data)} 只股票数据")
        print(f"❌ 失败 {failed_count} 只")
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

if __name__ == "__main__":
    fetcher = DataFetcher()
    stock_list = fetcher.get_stock_list()
    if stock_list is not None:
        print(f"测试成功，获取到 {len(stock_list)} 只股票")
    else:
        print("测试失败")