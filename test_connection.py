"""
网络连接和接口测试工具

这个文件专门用于测试：
1. 基础网络连接是否正常
2. AKShare各种数据接口是否可用
3. 数据库连接是否正常
4. 完整的数据下载流程测试

使用方法：
python test_connection.py

作者：Claude Code
"""

import akshare as ak
import requests
import time
import logging
from stock_database import StockDatabase
from stock_downloader import StockDownloader

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_network():
    """测试基础网络连接"""
    logger.info("🌐 测试基础网络连接...")
    
    test_urls = [
        ("百度", "https://www.baidu.com"),
        ("新浪", "https://www.sina.com.cn"),
        ("东方财富", "https://www.eastmoney.com")
    ]
    
    results = {}
    
    for name, url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"   ✅ {name} 连接正常")
                results[name] = True
            else:
                logger.warning(f"   ⚠️  {name} 状态码: {response.status_code}")
                results[name] = False
        except Exception as e:
            logger.error(f"   ❌ {name} 连接失败: {e}")
            results[name] = False
    
    return results

def test_database_connection():
    """测试数据库连接"""
    logger.info("\n🗄️  测试数据库连接...")
    
    try:
        db = StockDatabase()
        conn = db.get_connection()
        
        if conn:
            logger.info("   ✅ 数据库连接成功")
            
            # 检查表是否存在
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            if tables:
                logger.info(f"   📋 数据表: {tables}")
                
                # 检查股票基本信息数量
                cursor.execute("SELECT COUNT(*) FROM stock_basic_info")
                stock_count = cursor.fetchone()[0]
                logger.info(f"   📊 股票基本信息: {stock_count} 条")
                
                # 检查K线数据数量
                cursor.execute("SELECT COUNT(*) FROM stock_daily_kline")
                kline_count = cursor.fetchone()[0]
                logger.info(f"   📈 K线数据: {kline_count} 条")
                
            else:
                logger.warning("   ⚠️  数据库中无表，需要初始化")
            
            conn.close()
            return True
            
        else:
            logger.error("   ❌ 数据库连接失败")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ 数据库测试失败: {e}")
        return False

def test_akshare_interfaces():
    """测试AKShare数据接口"""
    logger.info("\n📊 测试AKShare数据接口...")
    
    # 测试接口列表
    tests = [
        {
            "name": "股票基本信息",
            "func": lambda: ak.stock_info_a_code_name(),
            "check": lambda data: len(data) > 1000
        },
        {
            "name": "新浪K线接口", 
            "func": lambda: ak.stock_zh_a_daily(
                symbol="sz000001", 
                start_date="20250825", 
                end_date="20250827", 
                adjust="qfq"
            ),
            "check": lambda data: len(data) >= 1
        },
        {
            "name": "东财K线接口",
            "func": lambda: ak.stock_zh_a_hist(
                symbol="000001",
                period="daily",
                start_date="20250827",
                end_date="20250827", 
                adjust="qfq"
            ),
            "check": lambda data: len(data) >= 1
        }
    ]
    
    results = {}
    
    for test in tests:
        logger.info(f"   📈 测试 {test['name']}...")
        
        try:
            start_time = time.time()
            data = test['func']()
            end_time = time.time()
            
            if data is not None and not data.empty and test['check'](data):
                logger.info(f"      ✅ 成功! 耗时: {end_time-start_time:.2f}秒，数据量: {len(data)}")
                results[test['name']] = True
            else:
                logger.warning(f"      ⚠️  数据异常或为空")
                results[test['name']] = False
                
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 80:
                error_msg = error_msg[:80] + "..."
            logger.error(f"      ❌ 失败: {error_msg}")
            results[test['name']] = False
        
        # 接口间延迟
        time.sleep(1)
    
    return results

def test_download_workflow():
    """测试完整的数据下载流程"""
    logger.info("\n🚀 测试完整数据下载流程...")
    
    try:
        # 创建下载器
        downloader = StockDownloader(delay_seconds=1.0)
        
        # 测试下载单只股票
        test_stock = "000001"
        logger.info(f"   📥 测试下载 {test_stock} 最近3天数据...")
        
        result = downloader.download_recent_days(test_stock, days=3, force_update=True)
        
        if result['success'] > 0:
            logger.info("      ✅ 数据下载流程测试成功!")
            logger.info(f"      📊 成功: {result['success']}, 失败: {result['failed']}")
            return True
        else:
            logger.error("      ❌ 数据下载流程测试失败")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ 下载流程测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    logger.info("🧪 开始全面连接测试")
    logger.info("=" * 60)
    
    # 测试结果收集
    all_results = {}
    
    # 1. 基础网络测试
    network_results = test_basic_network()
    all_results['network'] = network_results
    
    # 2. 数据库连接测试
    db_result = test_database_connection()
    all_results['database'] = db_result
    
    # 3. AKShare接口测试
    akshare_results = test_akshare_interfaces()
    all_results['akshare'] = akshare_results
    
    # 4. 完整流程测试
    workflow_result = test_download_workflow()
    all_results['workflow'] = workflow_result
    
    # 生成测试报告
    logger.info("\n" + "=" * 60)
    logger.info("📋 测试结果汇总")
    logger.info("=" * 60)
    
    # 网络连接结果
    logger.info("🌐 网络连接:")
    for site, result in network_results.items():
        status = "✅" if result else "❌"
        logger.info(f"   {status} {site}")
    
    # 数据库连接结果  
    logger.info("🗄️  数据库:")
    db_status = "✅" if db_result else "❌"
    logger.info(f"   {db_status} MySQL连接")
    
    # AKShare接口结果
    logger.info("📊 数据接口:")
    for interface, result in akshare_results.items():
        status = "✅" if result else "❌"
        logger.info(f"   {status} {interface}")
    
    # 完整流程结果
    logger.info("🚀 下载流程:")
    workflow_status = "✅" if workflow_result else "❌"
    logger.info(f"   {workflow_status} 完整流程测试")
    
    # 总结建议
    logger.info("\n💡 使用建议:")
    
    # 找出可用的接口
    working_interfaces = [k for k, v in akshare_results.items() if v]
    if working_interfaces:
        logger.info("✅ 可用接口:")
        for interface in working_interfaces:
            logger.info(f"   - {interface}")
    
    # 问题诊断
    failed_tests = []
    if not any(network_results.values()):
        failed_tests.append("网络连接问题")
    if not db_result:
        failed_tests.append("数据库连接问题")
    if not any(akshare_results.values()):
        failed_tests.append("所有数据接口不可用")
    if not workflow_result:
        failed_tests.append("数据下载流程问题")
    
    if failed_tests:
        logger.info("⚠️  发现问题:")
        for problem in failed_tests:
            logger.info(f"   - {problem}")
    else:
        logger.info("🎉 所有测试通过，系统运行正常!")
    
    return all_results

def quick_test():
    """快速测试（只测试关键功能）"""
    logger.info("⚡ 快速连接测试")
    logger.info("=" * 30)
    
    # 测试数据库
    db_ok = test_database_connection()
    
    # 测试新浪接口（最稳定的）
    logger.info("\n📊 测试新浪接口...")
    try:
        data = ak.stock_zh_a_daily(symbol="sz000001", start_date="20250827", end_date="20250827", adjust="qfq")
        sina_ok = not data.empty
        logger.info("   ✅ 新浪接口正常" if sina_ok else "   ❌ 新浪接口异常")
    except Exception as e:
        logger.error(f"   ❌ 新浪接口失败: {e}")
        sina_ok = False
    
    logger.info("\n🎯 快速测试结果:")
    logger.info(f"   数据库: {'✅' if db_ok else '❌'}")
    logger.info(f"   新浪接口: {'✅' if sina_ok else '❌'}")
    
    if db_ok and sina_ok:
        logger.info("🎉 核心功能正常，可以开始下载数据!")
    else:
        logger.info("⚠️  存在问题，建议运行完整测试: python test_connection.py --full")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="网络连接和接口测试")
    parser.add_argument("--full", action="store_true", help="运行完整测试")
    parser.add_argument("--quick", action="store_true", help="运行快速测试")
    
    args = parser.parse_args()
    
    if args.full:
        run_all_tests()
    elif args.quick:
        quick_test()
    else:
        # 默认运行快速测试
        quick_test()
        print("\n提示: 使用 --full 参数运行完整测试")