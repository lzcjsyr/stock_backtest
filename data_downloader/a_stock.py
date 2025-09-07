#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import akshare as ak
import pandas as pd
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

class AStockDataFetcher:
    """A股数据获取器"""
    
    def __init__(self, db_path: str, max_workers: int = 1, max_retries: int = 3):
        self.db_path = db_path
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.request_delay = 1.0
        self.preferred_api = "stock_zh_a_hist"  # 默认首选API
        self.db_lock = threading.Lock()
        self.request_count = 0  # 请求计数器
        self.batch_size = 30    # 每批30次请求
    
    def set_preferred_api(self, api_name: str):
        """设置首选API"""
        valid_apis = ["stock_zh_a_hist", "stock_zh_a_daily", "stock_zh_a_hist_tx"]
        if api_name in valid_apis:
            self.preferred_api = api_name
            logger.info(f"首选API已设置为: {api_name}")
        else:
            logger.warning(f"无效的API名称: {api_name}, 保持默认设置")
    
    def get_api_info(self):
        """获取API信息"""
        return {
            "stock_zh_a_hist": "东方财富 (数据最完整，包含所有技术指标)",
            "stock_zh_a_daily": "新浪财经 (包含成交量和换手率)",
            "stock_zh_a_hist_tx": "腾讯证券 (基础数据，缺少成交量)"
        }
    
    def retry_on_failure(self, func, *args, **kwargs):
        """重试机制装饰器"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}, 10秒后重试...")
                    time.sleep(10)  # 失败后等待10秒
                else:
                    logger.error(f"重试{self.max_retries}次后仍然失败: {e}")
                    raise e
    
    def get_stock_list(self) -> Optional[List[Dict]]:
        """获取A股股票列表"""
        try:
            logger.info("正在获取A股股票列表...")
            stock_list = ak.stock_info_a_code_name()
            logger.info(f"获取到 {len(stock_list)} 只股票")
            
            # 转换为字典列表
            result = []
            for _, row in stock_list.iterrows():
                result.append({
                    'code': row['code'],
                    'name': row['name']
                })
            return result
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return None
    
    def get_basic_info(self, stock_code: str) -> Optional[Dict]:
        """获取单只股票的基本信息"""
        def _fetch_basic_info():
            # 获取个股详细信息
            info_df = ak.stock_individual_info_em(symbol=stock_code)
            
            if info_df is None or len(info_df) == 0:
                raise Exception(f"未获取到股票 {stock_code} 的基本信息")
            
            # 将key-value格式的DataFrame转换为字典
            info_dict = dict(zip(info_df['item'], info_df['value']))
            
            # 提取关键字段
            basic_info = {
                'stock_code': stock_code,
                'stock_name': info_dict.get('股票简称', ''),
                'total_share': self._parse_number(info_dict.get('总股本', 0)),
                'float_share': self._parse_number(info_dict.get('流通股', 0)),
                'total_market_value': self._parse_number(info_dict.get('总市值', 0)),
                'float_market_value': self._parse_number(info_dict.get('流通市值', 0)),
                'industry': info_dict.get('行业', ''),
                'list_date': info_dict.get('上市时间', ''),
                'latest_price': self._parse_number(info_dict.get('最新价', 0))
            }
            
            return basic_info
        
        try:
            return self.retry_on_failure(_fetch_basic_info)
        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 基本信息失败: {e}")
            return None
    
    def get_kline_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """获取单只股票的日K线数据 - 三重备用API机制"""
        
        # 所有可用的API方法
        all_api_methods = {
            "stock_zh_a_hist": self._fetch_with_hist_api,
            "stock_zh_a_daily": self._fetch_with_daily_api, 
            "stock_zh_a_hist_tx": self._fetch_with_tx_api
        }
        
        # 根据首选API重新排序
        api_methods = []
        
        # 首先添加首选API
        if self.preferred_api in all_api_methods:
            api_methods.append((self.preferred_api, all_api_methods[self.preferred_api]))
        
        # 然后添加其他API作为备用
        for api_name, api_method in all_api_methods.items():
            if api_name != self.preferred_api:
                api_methods.append((api_name, api_method))
        
        # 依次尝试各个API
        for i, (api_name, api_method) in enumerate(api_methods):
            api_label = "首选" if i == 0 else f"备用{i}"
            try:
                logger.info(f"尝试 {api_label} API ({api_name}) 获取股票 {stock_code} K线数据...")
                data = self.retry_on_failure(api_method, stock_code, start_date, end_date)
                
                # 转换DataFrame为字典列表
                if data is not None and len(data) > 0:
                    result = []
                    for _, row in data.iterrows():
                        result.append(row.to_dict())
                    return result
            except Exception as e:
                logger.warning(f"{api_label} API ({api_name}) 失败: {e}")
                continue
        
        logger.error(f"所有API都失败，无法获取股票 {stock_code} 的K线数据")
        return None
    
    def _fetch_with_hist_api(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用stock_zh_a_hist API获取数据"""
        data = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"
        )
        
        if data is None or len(data) == 0:
            raise Exception(f"stock_zh_a_hist API未获取到股票 {stock_code} 的K线数据")
        
        # 重命名列名以匹配数据库字段
        column_mapping = {
            '日期': 'trade_date',
            '股票代码': 'stock_code', 
            '开盘': 'open_price',
            '收盘': 'close_price',
            '最高': 'high_price',
            '最低': 'low_price',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'change_pct',
            '涨跌额': 'change_amount',
            '换手率': 'turnover_rate'
        }
        
        existing_columns = {k: v for k, v in column_mapping.items() if k in data.columns}
        data = data.rename(columns=existing_columns)
        data['stock_code'] = stock_code
        
        if 'trade_date' in data.columns:
            data['trade_date'] = pd.to_datetime(data['trade_date']).dt.strftime('%Y-%m-%d')
        # 成交量单位规范化：东方财富为“手”→ 统一为“股”
        if 'volume' in data.columns:
            data['volume'] = (pd.to_numeric(data['volume'], errors='coerce').fillna(0) * 100).astype('int64')
        
        return data
    
    def _fetch_with_daily_api(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用stock_zh_a_daily API获取数据"""
        # 需要添加交易所前缀
        symbol_with_prefix = f"sz{stock_code}" if stock_code.startswith(('0', '3')) else f"sh{stock_code}"
        
        data = ak.stock_zh_a_daily(
            symbol=symbol_with_prefix,
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"
        )
        
        if data is None or len(data) == 0:
            raise Exception(f"stock_zh_a_daily API未获取到股票 {stock_code} 的K线数据")
        
        # stock_zh_a_daily的字段映射
        data = data.rename(columns={
            'date': 'trade_date',
            'open': 'open_price', 
            'close': 'close_price',
            'high': 'high_price',
            'low': 'low_price',
            'volume': 'volume',
            'amount': 'amount',
            'turnover': 'turnover_rate'
        })
        
        # 计算缺失字段
        if 'open_price' in data.columns and 'close_price' in data.columns:
            data['change_amount'] = data['close_price'] - data['open_price']
            data['change_pct'] = ((data['close_price'] - data['open_price']) / data['open_price'] * 100).round(2)
        
        if 'high_price' in data.columns and 'low_price' in data.columns and 'close_price' in data.columns:
            data['amplitude'] = ((data['high_price'] - data['low_price']) / data['close_price'] * 100).round(2)
        
        data['stock_code'] = stock_code
        data['trade_date'] = pd.to_datetime(data['trade_date']).dt.strftime('%Y-%m-%d')
        # 确保成交量为数字（新浪已是“股”）
        if 'volume' in data.columns:
            data['volume'] = pd.to_numeric(data['volume'], errors='coerce').fillna(0).astype('int64')
        
        return data
    
    def _fetch_with_tx_api(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用stock_zh_a_hist_tx API获取数据"""
        # 需要添加交易所前缀
        symbol_with_prefix = f"sz{stock_code}" if stock_code.startswith(('0', '3')) else f"sh{stock_code}"
        
        data = ak.stock_zh_a_hist_tx(
            symbol=symbol_with_prefix,
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"
        )
        
        if data is None or len(data) == 0:
            raise Exception(f"stock_zh_a_hist_tx API未获取到股票 {stock_code} 的K线数据")
        
        # stock_zh_a_hist_tx的字段映射
        data = data.rename(columns={
            'date': 'trade_date',
            'open': 'open_price', 
            'close': 'close_price',
            'high': 'high_price',
            'low': 'low_price',
            'amount': 'amount'
        })
        
        # 计算缺失字段
        if 'open_price' in data.columns and 'close_price' in data.columns:
            data['change_amount'] = data['close_price'] - data['open_price']
            data['change_pct'] = ((data['close_price'] - data['open_price']) / data['open_price'] * 100).round(2)
        
        if 'high_price' in data.columns and 'low_price' in data.columns and 'close_price' in data.columns:
            data['amplitude'] = ((data['high_price'] - data['low_price']) / data['close_price'] * 100).round(2)
        
        # 腾讯API：amount 实为成交量，单位“手” → 转为“股”
        if 'amount' in data.columns:
            data['volume'] = (pd.to_numeric(data['amount'], errors='coerce').fillna(0) * 100).astype('int64')
        else:
            data['volume'] = 0
        # 不强制保留换手率
        
        data['stock_code'] = stock_code
        data['trade_date'] = pd.to_datetime(data['trade_date']).dt.strftime('%Y-%m-%d')
        
        return data
    
    
    def get_financial_abstract(self, stock_code: str) -> Optional[pd.DataFrame]:
        """获取财务摘要数据（新API）"""
        import random
        
        # 检查是否需要批次等待
        if self.request_count >= self.batch_size:
            wait_time = random.uniform(60, 180)  # 1-3分钟
            logger.info(f"已完成 {self.request_count} 次请求，等待 {wait_time/60:.1f} 分钟...")
            time.sleep(wait_time)
            self.request_count = 0  # 重置计数器
        
        def _fetch_financial_abstract():
            # 每次请求间隔0-5秒
            delay = random.uniform(0, 5.0)
            time.sleep(delay)
            
            try:
                data = ak.stock_financial_abstract(symbol=stock_code)
                
                if data is None or len(data) == 0:
                    raise Exception(f"API返回空数据")
                
                return data
            except Exception as e:
                error_msg = str(e)
                if "Expecting value" in error_msg:
                    # JSON解析错误，可能是API限流或返回非JSON内容
                    logger.warning(f"股票 {stock_code} JSON解析失败，可能API限流")
                    raise Exception(f"API可能被限流，请稍后重试: {error_msg}")
                elif "404" in error_msg or "Not Found" in error_msg:
                    # 股票可能已退市或不存在
                    raise Exception(f"股票代码可能无效或已退市")
                else:
                    # 其他错误直接抛出
                    raise e
        
        try:
            result = self.retry_on_failure(_fetch_financial_abstract)
            if result is not None:
                self.request_count += 1  # 成功时增加计数器
            return result
        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 财务摘要失败: {e}")
            return None
    
    def get_stock_date_range(self, stock_code: str) -> tuple[str, str]:
        """获取股票的K线数据日期范围：从list_date到当天"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.execute(
                    "SELECT list_date FROM stock_basic_info WHERE stock_code = ?",
                    (stock_code,)
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    # list_date格式是YYYYMMDD，转换为YYYY-MM-DD
                    list_date_str = result[0]
                    try:
                        list_date = datetime.strptime(list_date_str, '%Y%m%d')
                        start_date = list_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # 如果解析失败，使用默认开始日期
                        logger.warning(f"股票 {stock_code} 的list_date格式异常: {list_date_str}, 使用默认开始日期")
                        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                else:
                    # 如果没有list_date，使用默认开始日期（一年前）
                    logger.warning(f"股票 {stock_code} 没有list_date，使用默认开始日期")
                    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                
                # 结束日期直接使用今天，AKShare API会自动处理非交易日
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                return start_date, end_date
                
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 日期范围失败: {e}")
            # 返回默认日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            return start_date, end_date
    
    def _parse_number(self, value) -> float:
        """解析数值，处理可能的字符串格式"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # 移除可能的单位和格式化字符
            value = value.replace(',', '').replace('万', '').replace('亿', '').replace('元', '')
            try:
                return float(value)
            except ValueError:
                return 0.0
        
        return 0.0