"""
股票数据下载器 - 核心下载功能

这是一个专注于数据下载的核心模块，功能清晰简单：
1. 使用稳定的新浪接口下载股票K线数据
2. 支持单只股票和批量下载
3. 自动保存到本地数据库
4. 智能重试和延迟控制

使用方法：
from stock_downloader import StockDownloader
downloader = StockDownloader()
downloader.download_stock('000001', '2025-08-01', '2025-08-27')

作者：Claude Code
依赖：stock_database.py, akshare
"""

import akshare as ak
import pandas as pd
from stock_database import StockDatabase
from datetime import datetime, timedelta
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockDownloader:
    """
    股票数据下载器
    
    专注于从网络下载股票数据并保存到本地数据库
    """
    
    def __init__(self, delay_seconds=1.0, max_retries=3):
        """
        初始化下载器
        
        Parameters:
        -----------
        delay_seconds : float
            请求间延迟时间（秒），防止被限制
        max_retries : int
            网络失败时的最大重试次数
        """
        self.db = StockDatabase()
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        
        logger.info(f"📥 股票下载器初始化完成")
        logger.info(f"   - 请求延迟: {delay_seconds}秒")
        logger.info(f"   - 最大重试: {max_retries}次")
    
    def _get_stock_symbol(self, stock_code):
        """
        获取新浪接口需要的股票代码格式
        
        Parameters:
        -----------
        stock_code : str
            原始股票代码，如 '000001'
            
        Returns:
        --------
        str
            带前缀的代码，如 'sz000001' 或 'sh600000'
        """
        # 上海股票：主板600/601/603、科创板688
        if stock_code.startswith(('60', '688')):
            return f"sh{stock_code}"
        # 深圳股票：主板000/001、创业板300
        elif stock_code.startswith(('000', '001', '002', '003', '300', '301')):
            return f"sz{stock_code}"
        # 北交所：8开头
        elif stock_code.startswith('8'):
            return f"bj{stock_code}"
        else:
            # 默认深圳
            return f"sz{stock_code}"
    
    def _convert_data_format(self, raw_data):
        """
        将新浪接口数据转换为数据库标准格式
        
        Parameters:
        -----------
        raw_data : DataFrame
            新浪接口原始数据
            
        Returns:
        --------
        DataFrame
            标准格式数据
        """
        if raw_data.empty:
            return raw_data
        
        try:
            # 创建副本避免修改原数据
            data = raw_data.copy()
            
            # 字段映射：新浪格式 -> 数据库格式
            column_mapping = {
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'amount': '成交额'
            }
            
            # 重命名字段
            data = data.rename(columns=column_mapping)
            
            # 添加默认字段（如果缺失）
            default_fields = {
                '涨跌幅': 0.0,
                '涨跌额': 0.0, 
                '换手率': 0.0,
                '振幅': 0.0
            }
            
            for field, default_value in default_fields.items():
                if field not in data.columns:
                    data[field] = default_value
            
            # 确保日期格式正确
            data['日期'] = pd.to_datetime(data['日期'])
            
            return data
            
        except Exception as e:
            logger.error(f"数据格式转换失败: {e}")
            return raw_data
    
    def download_single_stock(self, stock_code, start_date, end_date, force_update=False):
        """
        下载单只股票的K线数据
        
        Parameters:
        -----------
        stock_code : str
            股票代码，如 '000001'
        start_date : str
            开始日期，格式 'YYYY-MM-DD'
        end_date : str
            结束日期，格式 'YYYY-MM-DD'  
        force_update : bool
            是否强制更新（忽略已有数据）
            
        Returns:
        --------
        bool
            下载是否成功
        """
        try:
            # 检查是否已有数据（除非强制更新）
            if not force_update and self.db.check_kline_data_exists(stock_code, start_date, end_date):
                logger.info(f"📊 {stock_code} 数据已存在，跳过下载")
                return True
            
            logger.info(f"📥 开始下载 {stock_code} ({start_date} 到 {end_date})")
            
            # 准备参数
            symbol = self._get_stock_symbol(stock_code)
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')
            
            # 重试机制
            raw_data = None
            for attempt in range(self.max_retries):
                try:
                    # 调用新浪接口
                    raw_data = ak.stock_zh_a_daily(
                        symbol=symbol,
                        start_date=start_str,
                        end_date=end_str,
                        adjust="qfq"  # 前复权
                    )
                    
                    if not raw_data.empty:
                        break
                    else:
                        logger.warning(f"⚠️  {stock_code} 第{attempt+1}次尝试返回空数据")
                        
                except Exception as e:
                    logger.warning(f"⚠️  {stock_code} 第{attempt+1}次尝试失败: {e}")
                
                # 重试延迟
                if attempt < self.max_retries - 1:
                    retry_delay = 2 ** attempt  # 指数退避：1, 2, 4秒
                    time.sleep(retry_delay)
            
            # 检查是否获取到数据
            if raw_data is None or raw_data.empty:
                logger.error(f"❌ {stock_code} 下载失败，已重试{self.max_retries}次")
                return False
            
            # 转换数据格式
            standard_data = self._convert_data_format(raw_data)
            
            # 保存到数据库
            if self.db.save_daily_kline_data(standard_data, stock_code):
                logger.info(f"✅ {stock_code} 下载成功，保存 {len(standard_data)} 条数据")
                return True
            else:
                logger.error(f"❌ {stock_code} 保存到数据库失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ {stock_code} 下载过程出错: {e}")
            return False
    
    def download_multiple_stocks(self, stock_codes, start_date, end_date, force_update=False):
        """
        批量下载多只股票的K线数据
        
        Parameters:
        -----------
        stock_codes : list
            股票代码列表，如 ['000001', '000002', '600000']
        start_date : str
            开始日期，格式 'YYYY-MM-DD'
        end_date : str
            结束日期，格式 'YYYY-MM-DD'
        force_update : bool
            是否强制更新
            
        Returns:
        --------
        dict
            下载结果统计 {'success': 成功数量, 'failed': 失败数量, 'total': 总数量}
        """
        total_count = len(stock_codes)
        success_count = 0
        failed_count = 0
        
        logger.info(f"🚀 开始批量下载 {total_count} 只股票")
        logger.info(f"📅 时间范围: {start_date} 到 {end_date}")
        
        for i, stock_code in enumerate(stock_codes):
            logger.info(f"📈 进度: {i+1}/{total_count} - {stock_code}")
            
            # 下载单只股票
            if self.download_single_stock(stock_code, start_date, end_date, force_update):
                success_count += 1
            else:
                failed_count += 1
            
            # 延迟控制（最后一只股票不需要延迟）
            if i < total_count - 1:
                time.sleep(self.delay_seconds)
        
        # 统计结果
        result = {
            'success': success_count,
            'failed': failed_count,
            'total': total_count
        }
        
        logger.info(f"🎯 批量下载完成: 成功 {success_count}/{total_count}")
        if failed_count > 0:
            logger.warning(f"⚠️  失败 {failed_count} 只股票")
        
        return result
    
    def get_all_stock_codes(self):
        """
        从数据库获取所有活跃股票代码
        
        Returns:
        --------
        list
            股票代码列表
        """
        conn = self.db.get_connection()
        if not conn:
            logger.error("数据库连接失败")
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT stock_code FROM stock_basic_info WHERE is_active = 1")
            results = cursor.fetchall()
            stock_codes = [row[0] for row in results]
            logger.info(f"📋 从数据库获取到 {len(stock_codes)} 只活跃股票")
            return stock_codes
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
        finally:
            conn.close()
    
    def download_recent_days(self, stock_codes, days=30, force_update=False):
        """
        下载最近N天的数据
        
        Parameters:
        -----------
        stock_codes : list or str
            股票代码列表或单个代码
        days : int
            最近天数
        force_update : bool
            是否强制更新
            
        Returns:
        --------
        dict
            下载结果统计
        """
        # 处理单个股票代码的情况
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        logger.info(f"📅 下载最近{days}天的数据: {start_date} 到 {end_date}")
        
        return self.download_multiple_stocks(stock_codes, start_date, end_date, force_update)

# 便捷函数
def quick_download(stock_code, days=30):
    """
    快速下载单只股票最近N天的数据
    
    Parameters:
    -----------
    stock_code : str
        股票代码
    days : int
        最近天数
    """
    downloader = StockDownloader()
    return downloader.download_recent_days(stock_code, days)

def batch_download(stock_codes, days=30):
    """
    快速批量下载多只股票最近N天的数据
    
    Parameters:
    -----------
    stock_codes : list
        股票代码列表
    days : int
        最近天数
    """
    downloader = StockDownloader()
    return downloader.download_recent_days(stock_codes, days)

# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="股票数据下载器")
    parser.add_argument("--stock", nargs="+", required=True, help="股票代码，如 000001 600000")
    parser.add_argument("--days", type=int, default=30, help="最近天数，默认30天")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="强制更新，忽略已有数据")
    parser.add_argument("--delay", type=float, default=1.0, help="请求延迟时间（秒）")
    
    args = parser.parse_args()
    
    # 创建下载器
    downloader = StockDownloader(delay_seconds=args.delay)
    
    # 确定日期范围
    if args.start and args.end:
        # 使用指定日期范围
        result = downloader.download_multiple_stocks(
            args.stock, args.start, args.end, args.force
        )
    else:
        # 使用最近N天
        result = downloader.download_recent_days(
            args.stock, args.days, args.force
        )
    
    print(f"\n📊 下载结果:")
    print(f"   成功: {result['success']}")
    print(f"   失败: {result['failed']}")
    print(f"   总计: {result['total']}")