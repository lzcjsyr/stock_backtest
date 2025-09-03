"""
异步批量下载器 - 高速下载全部A股数据

这个脚本使用异步编程来大幅提升下载速度
支持并发下载、智能重试、断点续传

使用方法：
直接运行脚本，按提示输入参数即可
python async_batch_downloader.py

作者：Claude Code
"""

import asyncio
import akshare as ak
import pandas as pd
import argparse
from datetime import datetime, timedelta
from stock_database import StockDatabase
import logging
import threading

# ==================== 用户配置参数 ====================
# 以下参数可以根据需要调整

# 异步下载配置
DEFAULT_MAX_CONCURRENT = 10      # 默认最大并发下载数
DEFAULT_DELAY_SECONDS = 0.5      # 请求间延迟时间（秒）
DEFAULT_BATCH_SIZE = 200         # 每批处理的股票数量
DEFAULT_DAYS = 30                # 默认下载最近多少天的数据

# 网络配置  
MAX_RETRIES = 3                  # 网络失败时的最大重试次数

# 常用时间选项
COMMON_TIME_OPTIONS = {
    "1": ("最近7天", 7),
    "2": ("最近30天", 30), 
    "3": ("最近90天", 90),
    "4": ("最近180天", 180),
    "5": ("最近一年", 365),
    "6": ("自定义日期范围", None),
    "7": ("从指定日期到今天", None)
}

# 并发数选项
CONCURRENT_OPTIONS = {
    "1": ("保守模式", 5),
    "2": ("标准模式", 10),
    "3": ("激进模式", 20),
    "4": ("极速模式", 30),
    "5": ("自定义", None)
}

# ======================================================

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncStockDownloader:
    """
    异步股票下载器 - 高速并发下载
    """
    
    def __init__(self, max_concurrent=10, delay_seconds=0.5, max_retries=3):
        """
        初始化异步下载器
        
        Parameters:
        -----------
        max_concurrent : int
            最大并发下载数
        delay_seconds : float
            请求间延迟时间
        max_retries : int
            最大重试次数
        """
        self.db = StockDatabase()
        self.max_concurrent = max_concurrent
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.session = None
        
        # 统计变量
        self.success_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        
        logger.info(f"🚀 异步下载器初始化完成")
        logger.info(f"   - 最大并发: {max_concurrent}")
        logger.info(f"   - 请求延迟: {delay_seconds}秒")
        logger.info(f"   - 最大重试: {max_retries}次")
    
    def _get_stock_symbol(self, stock_code):
        """获取股票代码格式"""
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
            return f"sz{stock_code}"
    
    def _convert_data_format(self, raw_data):
        """转换数据格式"""
        if raw_data.empty:
            return raw_data
        
        try:
            data = raw_data.copy()
            
            # 字段映射
            column_mapping = {
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'amount': '成交额'
            }
            
            data = data.rename(columns=column_mapping)
            
            # 添加默认字段
            default_fields = {
                '涨跌幅': 0.0,
                '涨跌额': 0.0, 
                '换手率': 0.0,
                '振幅': 0.0
            }
            
            for field, default_value in default_fields.items():
                if field not in data.columns:
                    data[field] = default_value
            
            data['日期'] = pd.to_datetime(data['日期'])
            return data
            
        except Exception as e:
            logger.error(f"数据格式转换失败: {e}")
            return raw_data
    
    async def download_single_stock_async(self, stock_code, start_date, end_date, force_update=False):
        """
        异步下载单只股票数据
        """
        try:
            # 检查是否已有数据
            if not force_update and self.db.check_kline_data_exists(stock_code, start_date, end_date):
                with self.lock:
                    self.success_count += 1
                return True
            
            # 准备参数
            symbol = self._get_stock_symbol(stock_code)
            start_str = start_date.replace('-', '')
            end_str = end_date.replace('-', '')
            
            # 重试机制
            for attempt in range(self.max_retries):
                try:
                    # 在线程池中执行akshare调用（因为akshare不是异步的）
                    loop = asyncio.get_event_loop()
                    raw_data = await loop.run_in_executor(
                        None,
                        lambda: ak.stock_zh_a_daily(
                            symbol=symbol,
                            start_date=start_str,
                            end_date=end_str,
                            adjust="qfq"
                        )
                    )
                    
                    if not raw_data.empty:
                        # 转换格式并保存
                        standard_data = self._convert_data_format(raw_data)
                        if self.db.save_daily_kline_data(standard_data, stock_code):
                            with self.lock:
                                self.success_count += 1
                            return True
                        else:
                            raise Exception("保存数据库失败")
                    else:
                        raise Exception("返回空数据")
                        
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                    else:
                        logger.warning(f"❌ {stock_code} 下载失败: {e}")
            
            with self.lock:
                self.failed_count += 1
            return False
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 下载过程出错: {e}")
            with self.lock:
                self.failed_count += 1
            return False
    
    async def download_batch_async(self, stock_codes, start_date, end_date, force_update=False):
        """
        异步批量下载股票数据
        """
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_with_semaphore(stock_code):
            async with semaphore:
                result = await self.download_single_stock_async(
                    stock_code, start_date, end_date, force_update
                )
                # 添加延迟
                if self.delay_seconds > 0:
                    await asyncio.sleep(self.delay_seconds)
                return result
        
        # 创建所有任务
        tasks = [download_with_semaphore(code) for code in stock_codes]
        
        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results

class AsyncBatchDownloader:
    """
    异步批量下载器主类
    """
    
    def __init__(self, max_concurrent=10, delay_seconds=0.5, batch_size=200):
        """
        初始化
        
        Parameters:
        -----------
        max_concurrent : int
            最大并发数
        delay_seconds : float
            请求延迟
        batch_size : int
            每批处理数量
        """
        self.downloader = AsyncStockDownloader(max_concurrent, delay_seconds)
        self.batch_size = batch_size
        self.db = StockDatabase()
        
        logger.info(f"🚀 异步批量下载器初始化完成")
        logger.info(f"   - 每批股票数: {batch_size}")
    
    def get_all_stock_codes(self):
        """获取所有活跃股票代码"""
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
    
    async def download_all_stocks_async(self, days=None, start_date=None, end_date=None, force_update=False):
        """
        异步下载所有股票数据
        """
        # 获取所有股票
        all_stocks = self.get_all_stock_codes()
        total_stocks = len(all_stocks)
        
        if total_stocks == 0:
            logger.error("❌ 没有找到活跃股票")
            return
        
        # 计算日期范围
        if days:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        logger.info(f"📋 准备异步下载 {total_stocks} 只股票的数据")
        logger.info(f"📅 时间范围: {start_date} 到 {end_date}")
        
        start_time = datetime.now()
        logger.info(f"🕐 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 分批处理
        for i in range(0, total_stocks, self.batch_size):
            batch_stocks = all_stocks[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
            
            logger.info(f"\n📦 处理第 {batch_num}/{total_batches} 批 ({len(batch_stocks)} 只股票)")
            
            # 异步下载当前批次
            batch_start = datetime.now()
            await self.downloader.download_batch_async(
                batch_stocks, start_date, end_date, force_update
            )
            batch_end = datetime.now()
            
            # 显示批次结果
            batch_time = batch_end - batch_start
            speed = len(batch_stocks) / batch_time.total_seconds()
            
            logger.info(f"   ⚡ 批次耗时: {batch_time.total_seconds():.1f}秒")
            logger.info(f"   🏎️  批次速度: {speed:.1f} 股票/秒")
            
            # 显示总体进度
            processed = min(i + self.batch_size, total_stocks)
            progress = (processed / total_stocks) * 100
            logger.info(f"📊 总进度: {processed}/{total_stocks} ({progress:.1f}%)")
            logger.info(f"   成功: {self.downloader.success_count}, 失败: {self.downloader.failed_count}")
            
            # 估算剩余时间
            if processed > 0:
                elapsed = datetime.now() - start_time
                avg_time_per_stock = elapsed.total_seconds() / processed
                remaining_stocks = total_stocks - processed
                estimated_remaining = remaining_stocks * avg_time_per_stock
                
                if estimated_remaining > 60:
                    remaining_minutes = int(estimated_remaining / 60)
                    logger.info(f"⏱️  预计剩余: {remaining_minutes} 分钟")
        
        # 完成统计
        end_time = datetime.now()
        total_time = end_time - start_time
        
        logger.info(f"\n" + "="*60)
        logger.info(f"🎯 异步下载完成!")
        logger.info(f"   ✅ 成功: {self.downloader.success_count}")
        logger.info(f"   ❌ 失败: {self.downloader.failed_count}")
        logger.info(f"   📊 总计: {total_stocks}")
        logger.info(f"   🕐 总耗时: {total_time}")
        logger.info(f"   ⚡ 平均速度: {total_stocks/total_time.total_seconds():.2f} 股票/秒")

def get_user_input():
    """
    交互式获取用户输入参数
    """
    print("\n" + "="*60)
    print("⚡ 异步批量下载全部A股数据")
    print("="*60)
    
    # 显示时间选项
    print("\n📅 请选择下载时间范围：")
    for key, (desc, days) in COMMON_TIME_OPTIONS.items():
        print(f"   {key}. {desc}")
    
    # 获取时间选择
    while True:
        choice = input("\n请输入选项数字 (1-7): ").strip()
        if choice in COMMON_TIME_OPTIONS:
            break
        print("❌ 无效选项，请重新输入")
    
    desc, days = COMMON_TIME_OPTIONS[choice]
    print(f"✅ 已选择: {desc}")
    
    # 根据选择获取具体参数
    start_date = None
    end_date = None
    days_param = None
    
    if choice == "6":  # 自定义日期范围
        while True:
            try:
                start_date = input("请输入开始日期 (格式: 2025-08-01): ").strip()
                datetime.strptime(start_date, '%Y-%m-%d')
                break
            except ValueError:
                print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
        
        while True:
            try:
                end_date = input("请输入结束日期 (格式: 2025-08-27): ").strip()
                datetime.strptime(end_date, '%Y-%m-%d')
                break
            except ValueError:
                print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
    
    elif choice == "7":  # 从指定日期到今天
        while True:
            try:
                start_date = input("请输入开始日期 (格式: 2025-08-01): ").strip()
                datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                break
            except ValueError:
                print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
    
    else:  # 最近N天
        days_param = days
    
    # 获取并发配置
    print(f"\n🚀 请选择并发模式：")
    for key, (desc, concurrent) in CONCURRENT_OPTIONS.items():
        print(f"   {key}. {desc}" + (f" ({concurrent}并发)" if concurrent else ""))
    
    while True:
        concurrent_choice = input("\n请输入选项数字 (1-5): ").strip()
        if concurrent_choice in CONCURRENT_OPTIONS:
            break
        print("❌ 无效选项，请重新输入")
    
    desc, concurrent = CONCURRENT_OPTIONS[concurrent_choice]
    print(f"✅ 已选择: {desc}")
    
    if concurrent_choice == "5":  # 自定义
        while True:
            try:
                concurrent = int(input("请输入并发数 (建议5-30): "))
                if 1 <= concurrent <= 50:
                    break
                print("❌ 并发数应在1-50之间")
            except ValueError:
                print("❌ 请输入有效数字")
    
    # 获取其他参数
    print(f"\n⚙️  高级设置 (直接回车使用默认值):")
    
    # 延迟时间
    delay_input = input(f"请求延迟时间 (默认{DEFAULT_DELAY_SECONDS}秒): ").strip()
    delay = float(delay_input) if delay_input else DEFAULT_DELAY_SECONDS
    
    # 批次大小
    batch_input = input(f"每批处理股票数 (默认{DEFAULT_BATCH_SIZE}): ").strip()
    batch_size = int(batch_input) if batch_input else DEFAULT_BATCH_SIZE
    
    # 是否强制更新
    force_input = input("是否强制更新已有数据? (y/N): ").strip().lower()
    force_update = force_input in ['y', 'yes']
    
    return {
        'days': days_param,
        'start_date': start_date,
        'end_date': end_date,
        'concurrent': concurrent,
        'delay': delay,
        'batch_size': batch_size,
        'force_update': force_update
    }

def main():
    # 检查是否有命令行参数
    if len(__import__('sys').argv) > 1:
        # 使用命令行模式
        parser = argparse.ArgumentParser(description="异步批量下载全部A股数据")
        
        time_group = parser.add_mutually_exclusive_group(required=True)
        time_group.add_argument("--days", type=int, help="最近天数，如 30")
        time_group.add_argument("--date-range", nargs=2, metavar=("START", "END"), 
                               help="日期范围，如 2025-08-01 2025-08-27")
        time_group.add_argument("--from-date", metavar="START_DATE",
                               help="从指定日期到今天，如 2025-08-01")
        
        parser.add_argument("--concurrent", type=int, default=DEFAULT_MAX_CONCURRENT, help="最大并发数")
        parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="请求延迟时间（秒）")
        parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="每批处理股票数")
        parser.add_argument("--force", action="store_true", help="强制更新，忽略已有数据")
        
        args = parser.parse_args()
        
        params = {
            'concurrent': args.concurrent,
            'delay': args.delay,
            'batch_size': args.batch_size,
            'force_update': args.force
        }
        
        if args.days:
            params['days'] = args.days
        elif args.from_date:
            params['start_date'] = args.from_date
            params['end_date'] = datetime.now().strftime('%Y-%m-%d')
        else:
            params['start_date'], params['end_date'] = args.date_range
    
    else:
        # 使用交互模式
        params = get_user_input()
    
    # 显示配置信息
    print(f"\n⚡ 异步下载配置:")
    if params.get('days'):
        print(f"   📅 时间范围: 最近 {params['days']} 天")
    else:
        print(f"   📅 时间范围: {params['start_date']} 到 {params['end_date']}")
    print(f"   🚀 并发数量: {params['concurrent']}")
    print(f"   ⏱️  请求延迟: {params['delay']} 秒")
    print(f"   📦 批次大小: {params['batch_size']}")
    print(f"   🔄 强制更新: {'是' if params['force_update'] else '否'}")
    
    # 确认开始
    if len(__import__('sys').argv) == 1:  # 交互模式才需要确认
        confirm = input(f"\n确认开始异步下载? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("❌ 已取消下载")
            return
    
    # 创建异步批量下载器
    async_downloader = AsyncBatchDownloader(
        max_concurrent=params['concurrent'],
        delay_seconds=params['delay'],
        batch_size=params['batch_size']
    )
    
    # 运行异步下载
    async def run_download():
        if params.get('days'):
            await async_downloader.download_all_stocks_async(
                days=params['days'],
                force_update=params['force_update']
            )
        else:
            await async_downloader.download_all_stocks_async(
                start_date=params['start_date'],
                end_date=params['end_date'],
                force_update=params['force_update']
            )
    
    # 运行异步程序
    asyncio.run(run_download())

if __name__ == "__main__":
    main()