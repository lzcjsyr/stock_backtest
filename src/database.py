"""
数据库操作模块 - SQLite本地数据库
"""
import sqlite3
import pandas as pd
import os
from datetime import datetime

class StockDatabase:
    def __init__(self, db_path="data/stock_data.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 创建数据库表
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 股票基本信息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    update_time TIMESTAMP
                )
            """)
            
            # 股票价格数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    UNIQUE(symbol, date)
                )
            """)
            
            # 创建索引提升查询性能
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_date 
                ON stock_prices(symbol, date)
            """)
            
            print("✅ 数据库初始化完成")
    
    def save_stock_list(self, stock_df):
        """保存股票列表"""
        try:
            stock_df['update_time'] = datetime.now()
            with sqlite3.connect(self.db_path) as conn:
                stock_df.to_sql('stock_info', conn, if_exists='replace', index=False)
            print(f"✅ 已保存 {len(stock_df)} 只股票信息")
        except Exception as e:
            print(f"❌ 保存股票列表失败: {e}")
    
    def save_stock_prices(self, price_df):
        """保存股票价格数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                price_df.to_sql('stock_prices', conn, if_exists='append', index=False)
            print(f"✅ 已保存 {len(price_df)} 条价格数据")
        except Exception as e:
            print(f"❌ 保存价格数据失败: {e}")
    
    def get_stock_price_range(self, start_date, end_date):
        """获取指定时间范围的所有股票价格"""
        query = """
            SELECT * FROM stock_prices 
            WHERE date BETWEEN ? AND ?
            ORDER BY date, symbol
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=[start_date, end_date])
        
        return df
    
    def get_available_dates(self):
        """获取数据库中可用的日期范围"""
        query = """
            SELECT MIN(date) as start_date, MAX(date) as end_date, COUNT(*) as total_records
            FROM stock_prices
        """
        
        with sqlite3.connect(self.db_path) as conn:
            result = pd.read_sql_query(query, conn)
        
        return result.iloc[0] if len(result) > 0 else None

if __name__ == "__main__":
    db = StockDatabase()
    info = db.get_available_dates()
    if info is not None and info['total_records'] > 0:
        print(f"📊 数据库状态: {info['start_date']} 到 {info['end_date']}, 共 {info['total_records']} 条记录")
    else:
        print("📊 数据库为空，需要先获取数据")