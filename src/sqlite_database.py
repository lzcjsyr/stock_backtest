"""
SQLite多文件数据库管理模块

使用多个SQLite文件存储股票数据：
- stock_basic.db: 股票基本信息
- stock_prices.db: 股票价格数据
- stock_metadata.db: 元数据和配置

所有数据库文件存储在data/目录下
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SQLiteStockDatabase:
    """
    SQLite多文件股票数据库管理类
    """
    
    def __init__(self, data_dir="data"):
        """
        初始化数据库
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 数据库文件路径
        self.basic_db_path = os.path.join(self.data_dir, "stock_basic.db")
        self.prices_db_path = os.path.join(self.data_dir, "stock_prices.db")
        self.metadata_db_path = os.path.join(self.data_dir, "stock_metadata.db")
        
        # 初始化数据库表
        self._init_databases()
    
    @contextmanager
    def get_connection(self, db_path):
        """获取数据库连接上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式提升性能
            conn.execute("PRAGMA foreign_keys=ON")   # 启用外键约束
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_databases(self):
        """初始化所有数据库表结构"""
        self._init_basic_db()
        self._init_prices_db()
        self._init_metadata_db()
    
    def _init_basic_db(self):
        """初始化股票基本信息数据库"""
        with self.get_connection(self.basic_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    stock_code TEXT PRIMARY KEY,
                    stock_name TEXT NOT NULL,
                    market TEXT DEFAULT 'A',
                    list_date DATE,
                    industry TEXT,
                    concept TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_industry ON stock_info(industry)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_is_active ON stock_info(is_active)")
            
            conn.commit()
            logger.info("股票基本信息数据库初始化完成")
    
    def _init_prices_db(self):
        """初始化价格数据库"""
        with self.get_connection(self.prices_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    pct_change REAL,
                    price_change REAL,
                    turnover_rate REAL,
                    amplitude REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_daily_prices(stock_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_date ON stock_daily_prices(trade_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_daily_prices(stock_code, trade_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_close_price ON stock_daily_prices(close_price)")
            
            conn.commit()
            logger.info("股票价格数据库初始化完成")
    
    def _init_metadata_db(self):
        """初始化元数据数据库"""
        with self.get_connection(self.metadata_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    stock_code TEXT,
                    start_date DATE,
                    end_date DATE,
                    record_count INTEGER DEFAULT 0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("元数据数据库初始化完成")
    
    def save_stock_list(self, stock_df):
        """
        保存股票列表到基本信息数据库
        
        Args:
            stock_df: 包含股票信息的DataFrame
        """
        try:
            with self.get_connection(self.basic_db_path) as conn:
                # 准备数据
                stock_data = []
                for _, row in stock_df.iterrows():
                    stock_data.append({
                        'stock_code': str(row.get('code', '')),
                        'stock_name': str(row.get('name', '')),
                        'updated_at': datetime.now().isoformat()
                    })
                
                # 插入或更新数据
                for data in stock_data:
                    conn.execute("""
                        INSERT OR REPLACE INTO stock_info 
                        (stock_code, stock_name, updated_at) 
                        VALUES (?, ?, ?)
                    """, (data['stock_code'], data['stock_name'], data['updated_at']))
                
                conn.commit()
                logger.info(f"成功保存 {len(stock_data)} 条股票基本信息")
                
        except Exception as e:
            logger.error(f"保存股票列表失败: {e}")
            raise
    
    def save_stock_prices(self, price_df):
        """
        保存股票价格数据
        
        Args:
            price_df: 包含价格数据的DataFrame
        """
        try:
            with self.get_connection(self.prices_db_path) as conn:
                # 准备插入数据
                for _, row in price_df.iterrows():
                    conn.execute("""
                        INSERT OR REPLACE INTO stock_daily_prices 
                        (stock_code, trade_date, open_price, high_price, low_price, 
                         close_price, volume, amount, pct_change, price_change, 
                         turnover_rate, amplitude)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('symbol', ''),
                        row.get('date', ''),
                        float(row.get('open', 0)),
                        float(row.get('high', 0)),
                        float(row.get('low', 0)),
                        float(row.get('close', 0)),
                        int(row.get('volume', 0)),
                        float(row.get('amount', 0)),
                        float(row.get('pct_change', 0)) if pd.notnull(row.get('pct_change')) else None,
                        float(row.get('price_change', 0)) if pd.notnull(row.get('price_change')) else None,
                        float(row.get('turnover_rate', 0)) if pd.notnull(row.get('turnover_rate')) else None,
                        float(row.get('amplitude', 0)) if pd.notnull(row.get('amplitude')) else None
                    ))
                
                conn.commit()
                logger.info(f"成功保存 {len(price_df)} 条价格数据")
                
        except Exception as e:
            logger.error(f"保存价格数据失败: {e}")
            raise
    
    def get_stock_price_range(self, start_date, end_date):
        """
        获取指定时间范围的股票价格数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 价格数据
        """
        try:
            with self.get_connection(self.prices_db_path) as conn:
                query = """
                    SELECT stock_code as symbol, trade_date as date, 
                           open_price as open, high_price as high, 
                           low_price as low, close_price as close, 
                           volume, amount
                    FROM stock_daily_prices 
                    WHERE trade_date BETWEEN ? AND ?
                    ORDER BY trade_date, stock_code
                """
                
                df = pd.read_sql_query(query, conn, params=[start_date, end_date])
                return df
                
        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
            return pd.DataFrame()
    
    def get_available_dates(self):
        """
        获取数据库中可用的日期范围
        
        Returns:
            dict: 包含start_date, end_date, total_records的信息
        """
        try:
            with self.get_connection(self.prices_db_path) as conn:
                query = """
                    SELECT MIN(trade_date) as start_date, 
                           MAX(trade_date) as end_date, 
                           COUNT(*) as total_records
                    FROM stock_daily_prices
                """
                
                result = pd.read_sql_query(query, conn)
                if len(result) > 0 and result.iloc[0]['total_records'] > 0:
                    return result.iloc[0].to_dict()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"获取可用日期失败: {e}")
            return None
    
    def save_daily_kline_data(self, kline_data, stock_code):
        """
        保存单只股票的日K线数据（兼容旧接口）
        
        Args:
            kline_data: K线数据DataFrame
            stock_code: 股票代码
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 转换数据格式以匹配save_stock_prices方法
            price_data = []
            for _, row in kline_data.iterrows():
                price_data.append({
                    'symbol': stock_code,
                    'date': pd.to_datetime(row.get('日期')).date() if '日期' in row else row.get('date'),
                    'open': row.get('开盘', row.get('open', 0)),
                    'high': row.get('最高', row.get('high', 0)),
                    'low': row.get('最低', row.get('low', 0)),
                    'close': row.get('收盘', row.get('close', 0)),
                    'volume': row.get('成交量', row.get('volume', 0)),
                    'amount': row.get('成交额', row.get('amount', 0)),
                    'pct_change': row.get('涨跌幅', row.get('pct_change')),
                    'price_change': row.get('涨跌额', row.get('price_change')),
                    'turnover_rate': row.get('换手率', row.get('turnover_rate')),
                    'amplitude': row.get('振幅', row.get('amplitude'))
                })
            
            price_df = pd.DataFrame(price_data)
            self.save_stock_prices(price_df)
            
            return True
            
        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")
            return False
    
    def check_kline_data_exists(self, stock_code, start_date, end_date):
        """
        检查指定时间范围内的K线数据是否存在
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            bool: 数据是否充足
        """
        try:
            with self.get_connection(self.prices_db_path) as conn:
                query = """
                    SELECT COUNT(*) as count,
                           MIN(trade_date) as min_date,
                           MAX(trade_date) as max_date
                    FROM stock_daily_prices 
                    WHERE stock_code = ? 
                    AND trade_date BETWEEN ? AND ?
                """
                
                cursor = conn.cursor()
                cursor.execute(query, (stock_code, start_date, end_date))
                result = cursor.fetchone()
                
                if result and result[0] > 0:
                    # 简单的覆盖率检查：如果有数据就认为足够
                    # 这里可以根据需要实现更复杂的交易日覆盖率检查
                    expected_days = max((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days * 0.7, 1)
                    coverage = result[0] / expected_days
                    return coverage > 0.8
                
                return False
                
        except Exception as e:
            logger.error(f"检查K线数据存在性失败: {e}")
            return False
    
    def get_database_info(self):
        """
        获取数据库状态信息
        
        Returns:
            dict: 数据库状态信息
        """
        info = {
            'basic_db': os.path.getsize(self.basic_db_path) if os.path.exists(self.basic_db_path) else 0,
            'prices_db': os.path.getsize(self.prices_db_path) if os.path.exists(self.prices_db_path) else 0,
            'metadata_db': os.path.getsize(self.metadata_db_path) if os.path.exists(self.metadata_db_path) else 0
        }
        
        # 获取股票数量
        try:
            with self.get_connection(self.basic_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM stock_info WHERE is_active = 1")
                info['active_stocks'] = cursor.fetchone()[0]
        except:
            info['active_stocks'] = 0
        
        # 获取价格记录数量
        try:
            with self.get_connection(self.prices_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM stock_daily_prices")
                info['price_records'] = cursor.fetchone()[0]
        except:
            info['price_records'] = 0
        
        return info


# 兼容旧代码的别名
StockDatabase = SQLiteStockDatabase

if __name__ == "__main__":
    # 测试数据库
    db = SQLiteStockDatabase()
    info = db.get_database_info()
    print(f"数据库状态: {info}")
    
    dates_info = db.get_available_dates()
    if dates_info:
        print(f"数据范围: {dates_info['start_date']} 到 {dates_info['end_date']}")
        print(f"总记录数: {dates_info['total_records']}")
    else:
        print("数据库为空")