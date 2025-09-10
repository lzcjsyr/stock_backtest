#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseWriter:
    """统一的数据库写入器"""
    
    def __init__(self, db_path: str, db_init=None):
        self.db_path = db_path
        self.db_init = db_init
    
    def write_stock_list(self, stock_list_data: List[Dict]) -> int:
        """写入股票清单数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            # 清空旧数据
            conn.execute("DELETE FROM stock_list")
            
            # 插入新数据
            valid_count = 0
            filtered_count = 0
            for stock_data in stock_list_data:
                stock_code = stock_data['code']
                # 过滤股票代码（只保留6/3/0开头）
                if stock_code.startswith(('6', '3', '0')):
                    conn.execute("""
                        INSERT INTO stock_list (stock_code, stock_name) 
                        VALUES (?, ?)
                    """, (stock_code, stock_data['name']))
                    valid_count += 1
                else:
                    filtered_count += 1
            
            conn.commit()
            logger.info(f"✅ 股票清单写入成功: 有效股票 {valid_count} 只，过滤 {filtered_count} 只 (仅保留沪深交易所6/3/0开头)")
            return valid_count
    
    def write_basic_info(self, stock_code: str, basic_info: Dict) -> bool:
        """写入股票基本信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("""
                    INSERT OR REPLACE INTO stock_basic_info 
                    (stock_code, stock_name, total_share, float_share, 
                     total_market_value, float_market_value, industry, 
                     list_date, latest_price, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    basic_info['stock_code'],
                    basic_info['stock_name'],
                    basic_info['total_share'],
                    basic_info['float_share'],
                    basic_info['total_market_value'],
                    basic_info['float_market_value'],
                    basic_info['industry'],
                    basic_info['list_date'],
                    basic_info['latest_price']
                ))
                conn.commit()
            
            logger.info(f"✅ 股票 {stock_code} 基本信息写入成功: {basic_info['stock_name']} ({basic_info['industry']})")
            return True
        except Exception as e:
            logger.error(f"写入基本信息失败 {stock_code}: {e}")
            return False
    
    def write_kline_data(self, stock_code: str, kline_data: List[Dict], start_date: str, end_date: str) -> int:
        """写入K线数据"""
        if not kline_data:
            return 0
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                record_count = 0
                for row_data in kline_data:
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO stock_daily_kline 
                            (stock_code, trade_date, open_price, close_price, high_price, low_price, volume)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row_data.get('stock_code', stock_code),
                            row_data.get('trade_date'),
                            row_data.get('open_price', 0),
                            row_data.get('close_price', 0),
                            row_data.get('high_price', 0),
                            row_data.get('low_price', 0),
                            row_data.get('volume', 0)
                        ))
                        record_count += 1
                    except Exception as e:
                        logger.warning(f"保存股票 {stock_code} 单条数据失败: {e}")
                
                conn.commit()
                logger.info(f"✅ 股票 {stock_code} K线数据写入成功: {record_count} 条记录 ({start_date} ~ {end_date})")
                return record_count
        except Exception as e:
            logger.error(f"写入K线数据失败 {stock_code}: {e}")
            return 0
    
    
    def write_financial_abstract(self, stock_code: str, stock_name: str, df: pd.DataFrame) -> int:
        """写入财务摘要数据到SQLite"""
        try:
            # 转换为长格式
            df_long = df.melt(
                id_vars=['选项', '指标'], 
                var_name='report_date',
                value_name='value'
            )
            
            # 过滤空值并添加股票信息
            df_long = df_long.dropna(subset=['value'])
            df_long['stock_code'] = stock_code
            df_long['stock_name'] = stock_name
            df_long['category'] = df_long['选项']
            df_long['indicator'] = df_long['指标']
            
            # 准备写入数据
            records = df_long[['stock_code', 'stock_name', 'category', 'indicator', 'report_date', 'value']].to_dict('records')
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # 批量插入或更新
                cursor = conn.cursor()
                insert_count = 0
                
                for record in records:
                    cursor.execute("""
                        INSERT OR REPLACE INTO stock_financial_abstract 
                        (stock_code, stock_name, category, indicator, report_date, value, update_time)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        record['stock_code'],
                        record['stock_name'], 
                        record['category'],
                        record['indicator'],
                        record['report_date'],
                        record['value']
                    ))
                    insert_count += 1
                
                conn.commit()
                logger.info(f"✅ 股票 {stock_code} 财务摘要写入成功: {insert_count} 条记录")
                return insert_count
                
        except Exception as e:
            logger.error(f"写入财务摘要失败 {stock_code}: {e}")
            return 0