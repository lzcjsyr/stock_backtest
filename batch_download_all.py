"""
批量下载全部A股数据的脚本

这个脚本用于下载数据库中所有活跃股票的K线数据
支持分批下载、断点续传、错误重试

使用方法：
直接运行脚本，按提示输入参数即可
python batch_download_all.py

作者：Claude Code
"""

import time
import argparse
from datetime import datetime
from stock_downloader import StockDownloader
import logging

# ==================== 用户配置参数 ====================
# 以下参数可以根据需要调整

# 默认配置
DEFAULT_DELAY_SECONDS = 1.0      # 请求间延迟时间（秒），防止被限制
DEFAULT_BATCH_SIZE = 100         # 每批处理的股票数量
DEFAULT_DAYS = 30                # 默认下载最近多少天的数据

# 网络配置
MAX_RETRIES = 3                  # 网络失败时的最大重试次数
BATCH_REST_SECONDS = 3           # 批次间休息时间（秒）

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

# ======================================================

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchDownloader:
    """
    批量下载器 - 专门用于下载全部A股数据
    """
    
    def __init__(self, delay_seconds=1.0, batch_size=100):
        """
        初始化批量下载器
        
        Parameters:
        -----------
        delay_seconds : float
            每个股票下载间的延迟时间
        batch_size : int
            每批处理的股票数量
        """
        self.downloader = StockDownloader(delay_seconds=delay_seconds)
        self.batch_size = batch_size
        self.delay_seconds = delay_seconds
        
        logger.info(f"🚀 批量下载器初始化完成")
        logger.info(f"   - 每批股票数: {batch_size}")
        logger.info(f"   - 请求延迟: {delay_seconds}秒")
    
    def download_all_stocks(self, days=None, start_date=None, end_date=None, force_update=False):
        """
        下载所有股票的数据
        
        Parameters:
        -----------
        days : int, optional
            最近天数，与start_date/end_date二选一
        start_date : str, optional
            开始日期 YYYY-MM-DD
        end_date : str, optional
            结束日期 YYYY-MM-DD
        force_update : bool
            是否强制更新
        """
        # 获取所有活跃股票
        all_stocks = self.downloader.get_all_stock_codes()
        total_stocks = len(all_stocks)
        
        if total_stocks == 0:
            logger.error("❌ 没有找到活跃股票，请检查数据库")
            return
        
        logger.info(f"📋 准备下载 {total_stocks} 只股票的数据")
        
        # 显示时间范围
        if days:
            logger.info(f"📅 时间范围: 最近 {days} 天")
        else:
            logger.info(f"📅 时间范围: {start_date} 到 {end_date}")
        
        # 统计变量
        total_success = 0
        total_failed = 0
        processed = 0
        
        # 开始时间
        start_time = datetime.now()
        logger.info(f"🕐 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 分批处理
        for i in range(0, total_stocks, self.batch_size):
            batch_stocks = all_stocks[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
            
            logger.info(f"\n📦 处理第 {batch_num}/{total_batches} 批 ({len(batch_stocks)} 只股票)")
            logger.info(f"   股票代码: {', '.join(batch_stocks[:10])}{'...' if len(batch_stocks) > 10 else ''}")
            
            # 下载当前批次
            if days:
                result = self.downloader.download_recent_days(batch_stocks, days, force_update)
            else:
                result = self.downloader.download_multiple_stocks(
                    batch_stocks, start_date, end_date, force_update
                )
            
            # 更新统计
            total_success += result['success']
            total_failed += result['failed']
            processed += len(batch_stocks)
            
            # 显示进度
            progress = (processed / total_stocks) * 100
            logger.info(f"📊 进度: {processed}/{total_stocks} ({progress:.1f}%)")
            logger.info(f"   当前批次: 成功 {result['success']}, 失败 {result['failed']}")
            logger.info(f"   累计: 成功 {total_success}, 失败 {total_failed}")
            
            # 估算剩余时间
            if processed > 0:
                elapsed = datetime.now() - start_time
                avg_time_per_stock = elapsed.total_seconds() / processed
                remaining_stocks = total_stocks - processed
                estimated_remaining = remaining_stocks * avg_time_per_stock
                
                if estimated_remaining > 60:
                    remaining_minutes = int(estimated_remaining / 60)
                    logger.info(f"⏱️  预计剩余时间: {remaining_minutes} 分钟")
            
            # 批次间休息（避免请求过频）
            if i + self.batch_size < total_stocks:  # 不是最后一批
                batch_delay = 3  # 批次间休息3秒
                logger.info(f"😴 批次间休息 {batch_delay} 秒...")
                time.sleep(batch_delay)
        
        # 完成统计
        end_time = datetime.now()
        total_time = end_time - start_time
        
        logger.info(f"\n" + "="*60)
        logger.info(f"🎯 批量下载完成!")
        logger.info(f"   ✅ 成功: {total_success}")
        logger.info(f"   ❌ 失败: {total_failed}")
        logger.info(f"   📊 总计: {total_stocks}")
        logger.info(f"   🕐 耗时: {total_time}")
        logger.info(f"   ⚡ 平均速度: {total_stocks/total_time.total_seconds():.2f} 股票/秒")
        
        if total_failed > 0:
            logger.warning(f"⚠️  有 {total_failed} 只股票下载失败，可以稍后重新运行")
        else:
            logger.info(f"🎉 所有股票下载成功!")

def get_user_input():
    """
    交互式获取用户输入参数
    """
    print("\n" + "="*60)
    print("📈 批量下载全部A股数据")
    print("="*60)
    
    # 显示时间选项
    print("\n📅 请选择下载时间范围：")
    for key, (desc, days) in COMMON_TIME_OPTIONS.items():
        print(f"   {key}. {desc}")
    
    # 获取用户选择
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
        'delay': delay,
        'batch_size': batch_size,
        'force_update': force_update
    }

def main():
    # 检查是否有命令行参数
    if len(__import__('sys').argv) > 1:
        # 使用命令行模式
        parser = argparse.ArgumentParser(description="批量下载全部A股数据")
        
        time_group = parser.add_mutually_exclusive_group(required=True)
        time_group.add_argument("--days", type=int, help="最近天数，如 30")
        time_group.add_argument("--date-range", nargs=2, metavar=("START", "END"), 
                               help="日期范围，如 2025-08-01 2025-08-27")
        time_group.add_argument("--from-date", metavar="START_DATE",
                               help="从指定日期到今天，如 2025-08-01")
        
        parser.add_argument("--force", action="store_true", help="强制更新，忽略已有数据")
        parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="请求延迟时间（秒）")
        parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="每批处理股票数")
        
        args = parser.parse_args()
        
        params = {
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
    print(f"\n🚀 开始下载配置:")
    if params.get('days'):
        print(f"   📅 时间范围: 最近 {params['days']} 天")
    else:
        print(f"   📅 时间范围: {params['start_date']} 到 {params['end_date']}")
    print(f"   ⏱️  请求延迟: {params['delay']} 秒")
    print(f"   📦 批次大小: {params['batch_size']}")
    print(f"   🔄 强制更新: {'是' if params['force_update'] else '否'}")
    
    # 确认开始
    if len(__import__('sys').argv) == 1:  # 交互模式才需要确认
        confirm = input(f"\n确认开始下载? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("❌ 已取消下载")
            return
    
    # 创建批量下载器
    batch_downloader = BatchDownloader(
        delay_seconds=params['delay'],
        batch_size=params['batch_size']
    )
    
    # 开始下载
    if params.get('days'):
        batch_downloader.download_all_stocks(
            days=params['days'],
            force_update=params['force_update']
        )
    else:
        batch_downloader.download_all_stocks(
            start_date=params['start_date'],
            end_date=params['end_date'],
            force_update=params['force_update']
        )

if __name__ == "__main__":
    main()