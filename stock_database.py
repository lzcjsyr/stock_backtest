"""
股票数据库管理模块

本模块提供股票数据的数据库存储和管理功能，支持：
1. 数据库连接管理
2. 数据表创建和维护
3. 股票基本信息和K线数据的存储和查询
4. 数据完整性检查

主要数据表：
- stock_basic_info: 股票基本信息（代码、名称、市值、PE/PB等）
- stock_daily_kline: 股票日K线数据（前复权）
- stock_industry: 行业分类信息
- stock_concept: 概念板块信息
- stock_*_relation: 股票与行业/概念的关联关系

作者：Claude Code
依赖：pymysql, pandas, akshare
"""

import pymysql
import pandas as pd
import akshare as ak
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDatabase:
    """
    股票数据库管理类
    
    负责管理MySQL数据库连接、创建表结构以及执行CRUD操作
    """
    
    def __init__(self):
        """
        初始化数据库配置
        
        配置参数包括：
        - host: 数据库主机地址（localhost）
        - port: 数据库端口（3306）
        - user: 数据库用户名（stockuser）
        - password: 数据库密码
        - database: 数据库名称（stock_data）
        """
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'stockuser',
            'password': 'stock123456',
            'database': 'stock_data',
            'charset': 'utf8mb4'
        }
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = pymysql.connect(**self.config)
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def create_tables(self):
        """创建股票数据表"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 1. 股票基本信息表
            stock_basic_sql = """
            CREATE TABLE IF NOT EXISTS stock_basic_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
                stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
                market VARCHAR(10) DEFAULT 'A' COMMENT '市场(A股)',
                list_date DATE COMMENT '上市日期',
                total_market_value DECIMAL(20,2) COMMENT '总市值(亿元)',
                circulating_market_value DECIMAL(20,2) COMMENT '流通市值(亿元)',
                industry VARCHAR(100) COMMENT '所属行业',
                concept VARCHAR(500) COMMENT '概念板块',
                pe_ratio DECIMAL(10,4) COMMENT 'PE市盈率',
                pb_ratio DECIMAL(10,4) COMMENT 'PB市净率',
                is_active TINYINT(1) DEFAULT 1 COMMENT '是否活跃(1活跃0停牌等)',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_stock_code (stock_code),
                INDEX idx_industry (industry),
                INDEX idx_market_value (total_market_value)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息表'
            """
            
            # 2. 日K线数据表(前复权)
            daily_kline_sql = """
            CREATE TABLE IF NOT EXISTS stock_daily_kline (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
                trade_date DATE NOT NULL COMMENT '交易日期',
                open_price DECIMAL(10,4) NOT NULL COMMENT '开盘价(前复权)',
                high_price DECIMAL(10,4) NOT NULL COMMENT '最高价(前复权)',
                low_price DECIMAL(10,4) NOT NULL COMMENT '最低价(前复权)',
                close_price DECIMAL(10,4) NOT NULL COMMENT '收盘价(前复权)',
                volume BIGINT NOT NULL COMMENT '成交量(手)',
                amount DECIMAL(20,2) NOT NULL COMMENT '成交额(元)',
                pct_change DECIMAL(8,4) COMMENT '涨跌幅(%)',
                price_change DECIMAL(10,4) COMMENT '涨跌额(元)',
                turnover_rate DECIMAL(8,4) COMMENT '换手率(%)',
                amplitude DECIMAL(8,4) COMMENT '振幅(%)',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_stock_trade_date (stock_code, trade_date),
                INDEX idx_trade_date (trade_date),
                INDEX idx_stock_code (stock_code),
                INDEX idx_close_price (close_price)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日K线数据表(前复权)'
            """
            
            # 3. 行业分类表
            industry_sql = """
            CREATE TABLE IF NOT EXISTS stock_industry (
                id INT AUTO_INCREMENT PRIMARY KEY,
                industry_code VARCHAR(20) NOT NULL COMMENT '行业代码',
                industry_name VARCHAR(100) NOT NULL COMMENT '行业名称',
                parent_industry VARCHAR(100) COMMENT '上级行业',
                industry_level TINYINT DEFAULT 1 COMMENT '行业级别(1一级2二级3三级)',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_industry_code (industry_code),
                INDEX idx_industry_name (industry_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行业分类表'
            """
            
            # 4. 概念板块表
            concept_sql = """
            CREATE TABLE IF NOT EXISTS stock_concept (
                id INT AUTO_INCREMENT PRIMARY KEY,
                concept_code VARCHAR(20) NOT NULL COMMENT '概念代码',
                concept_name VARCHAR(100) NOT NULL COMMENT '概念名称',
                concept_desc TEXT COMMENT '概念描述',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_concept_code (concept_code),
                INDEX idx_concept_name (concept_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='概念板块表'
            """
            
            # 5. 股票行业关联表
            stock_industry_rel_sql = """
            CREATE TABLE IF NOT EXISTS stock_industry_relation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
                industry_code VARCHAR(20) NOT NULL COMMENT '行业代码',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_stock_industry (stock_code, industry_code),
                INDEX idx_stock_code (stock_code),
                INDEX idx_industry_code (industry_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票行业关联表'
            """
            
            # 6. 股票概念关联表
            stock_concept_rel_sql = """
            CREATE TABLE IF NOT EXISTS stock_concept_relation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
                concept_code VARCHAR(20) NOT NULL COMMENT '概念代码',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_stock_concept (stock_code, concept_code),
                INDEX idx_stock_code (stock_code),
                INDEX idx_concept_code (concept_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票概念关联表'
            """
            
            # 执行建表语句
            tables = [
                ("stock_basic_info", stock_basic_sql),
                ("stock_daily_kline", daily_kline_sql),
                ("stock_industry", industry_sql),
                ("stock_concept", concept_sql),
                ("stock_industry_relation", stock_industry_rel_sql),
                ("stock_concept_relation", stock_concept_rel_sql)
            ]
            
            for table_name, sql in tables:
                cursor.execute(sql)
                logger.info(f"表 {table_name} 创建成功")
            
            conn.commit()
            logger.info("所有数据表创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_stock_basic_info(self, stock_data):
        """保存股票基本信息"""
        if stock_data.empty:
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO stock_basic_info 
            (stock_code, stock_name, total_market_value, circulating_market_value, 
             pe_ratio, pb_ratio, is_active) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            stock_name=VALUES(stock_name),
            total_market_value=VALUES(total_market_value),
            circulating_market_value=VALUES(circulating_market_value),
            pe_ratio=VALUES(pe_ratio),
            pb_ratio=VALUES(pb_ratio),
            is_active=VALUES(is_active),
            updated_at=CURRENT_TIMESTAMP
            """
            
            data_to_insert = []
            for _, row in stock_data.iterrows():
                data_to_insert.append((
                    str(row.get('代码', '')),
                    str(row.get('名称', '')),
                    float(row.get('总市值', 0)) / 100000000 if pd.notnull(row.get('总市值', 0)) else None,  # 转为亿元
                    float(row.get('流通市值', 0)) / 100000000 if pd.notnull(row.get('流通市值', 0)) else None,
                    float(row.get('市盈率-动态', 0)) if pd.notnull(row.get('市盈率-动态', 0)) else None,
                    float(row.get('市净率', 0)) if pd.notnull(row.get('市净率', 0)) else None,
                    1  # 默认活跃
                ))
            
            cursor.executemany(insert_sql, data_to_insert)
            conn.commit()
            
            logger.info(f"成功保存 {len(data_to_insert)} 条股票基本信息")
            return True
            
        except Exception as e:
            logger.error(f"保存股票基本信息失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_daily_kline_data(self, kline_data, stock_code):
        """保存日K线数据(前复权)"""
        if kline_data.empty:
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO stock_daily_kline 
            (stock_code, trade_date, open_price, high_price, low_price, close_price, 
             volume, amount, pct_change, price_change, turnover_rate, amplitude) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open_price=VALUES(open_price),
            high_price=VALUES(high_price),
            low_price=VALUES(low_price),
            close_price=VALUES(close_price),
            volume=VALUES(volume),
            amount=VALUES(amount),
            pct_change=VALUES(pct_change),
            price_change=VALUES(price_change),
            turnover_rate=VALUES(turnover_rate),
            amplitude=VALUES(amplitude)
            """
            
            def _safe_float(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    return float(val)
                except Exception:
                    return default

            def _safe_int(val, default=0):
                try:
                    if pd.isna(val):
                        return default
                    return int(float(val))
                except Exception:
                    return default

            data_to_insert = []
            for _, row in kline_data.iterrows():
                trade_date = pd.to_datetime(row.get('日期')).date()
                data_to_insert.append((
                    stock_code,
                    trade_date,
                    _safe_float(row.get('开盘', 0.0)),
                    _safe_float(row.get('最高', 0.0)),
                    _safe_float(row.get('最低', 0.0)),
                    _safe_float(row.get('收盘', 0.0)),
                    _safe_int(row.get('成交量', 0)),
                    _safe_float(row.get('成交额', 0.0)),
                    _safe_float(row.get('涨跌幅', 0.0)),
                    _safe_float(row.get('涨跌额', 0.0)),
                    _safe_float(row.get('换手率', 0.0)),
                    _safe_float(row.get('振幅', 0.0))
                ))
            
            cursor.executemany(insert_sql, data_to_insert)
            conn.commit()
            
            logger.info(f"成功保存 {stock_code} 的 {len(data_to_insert)} 条K线数据")
            return True
            
        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_daily_kline_data(self, stock_code, start_date=None, end_date=None):
        """获取日K线数据"""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            sql = """
            SELECT trade_date, open_price, high_price, low_price, close_price, 
                   volume, amount, pct_change, price_change, turnover_rate, amplitude 
            FROM stock_daily_kline 
            WHERE stock_code = %s
            """
            params = [stock_code]
            
            if start_date:
                sql += " AND trade_date >= %s"
                params.append(start_date)
            
            if end_date:
                sql += " AND trade_date <= %s"
                params.append(end_date)
            
            sql += " ORDER BY trade_date"
            
            df = pd.read_sql(sql, conn, params=params, index_col='trade_date')
            
            # 重命名列以匹配akshare格式
            column_mapping = {
                'open_price': '开盘',
                'high_price': '最高', 
                'low_price': '最低',
                'close_price': '收盘',
                'volume': '成交量',
                'amount': '成交额',
                'pct_change': '涨跌幅',
                'price_change': '涨跌额',
                'turnover_rate': '换手率',
                'amplitude': '振幅'
            }
            df = df.rename(columns=column_mapping)
            
            logger.info(f"从数据库获取到 {stock_code} 的 {len(df)} 条K线数据")
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def check_kline_data_exists(self, stock_code, start_date, end_date):
        """检查指定时间范围内的K线数据是否存在(基于交易日历更准确地计算覆盖率)"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            sql = """
            SELECT COUNT(*) as count,
                   MIN(trade_date) as min_date,
                   MAX(trade_date) as max_date
            FROM stock_daily_kline 
            WHERE stock_code = %s 
            AND trade_date BETWEEN %s AND %s
            """
            
            cursor.execute(sql, (stock_code, start_date, end_date))
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                # 使用交易日历计算应有交易日数量
                try:
                    cal = ak.tool_trade_date_hist_sina()
                    cal['trade_date'] = pd.to_datetime(cal['trade_date'])
                    s = pd.to_datetime(start_date)
                    e = pd.to_datetime(end_date)
                    expected_days = int(((cal['trade_date'] >= s) & (cal['trade_date'] <= e)).sum())
                except Exception:
                    # 回退到粗略估算
                    expected_days = max(int((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days * 0.7), 1)
                coverage = result[0] / max(expected_days, 1)
                
                logger.info(f"{stock_code} 在 {start_date} 到 {end_date} 期间有 {result[0]} 条K线数据")
                return coverage > 0.9
            
            return False
            
        except Exception as e:
            logger.error(f"检查K线数据存在性失败: {e}")
            return False
        finally:
            conn.close()

# 使用示例
if __name__ == "__main__":
    db = StockDatabase()
    
    # 创建表
    if db.create_tables():
        print("数据表创建成功")
    
    # 测试连接
    conn = db.get_connection()
    if conn:
        print("数据库连接成功")
        conn.close()
    else:
        print("数据库连接失败")