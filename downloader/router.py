#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .sources.a_stock.initializer import DatabaseInitializer
from .sources.a_stock.writer import DatabaseWriter
from .sources.a_stock.fetcher import AStockDataFetcher
from .sources.a_stock.interface import CLIInterface

logger = logging.getLogger(__name__)

class DataRouter:
    """数据路由器 - 协调数据获取和存储"""
    
    def __init__(self, asset_type: str = "a_stock"):
        # 初始化数据库 - 支持多资产类型
        self.asset_type = asset_type
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_init = DatabaseInitializer(self.base_dir, asset_type)
        self.db_init.init_sqlite_database()
        
        # 获取数据库路径
        self.db_path = self.db_init.get_db_path()
        
        # 初始化组件
        self.db_writer = DatabaseWriter(self.db_path, self.db_init)
        self.a_stock_fetcher = AStockDataFetcher(self.db_path)
        self.cli = CLIInterface(self.db_path, self.db_init)
    
    def start(self):
        """启动路由器主循环"""
        while True:
            try:
                asset_choice = self.cli.show_asset_selection_menu()
                
                if asset_choice == "exit":
                    break
                elif asset_choice == "a_stock":
                    self._handle_a_stock()
                elif asset_choice is None:
                    # 无效选择或未实现功能，继续循环
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 数据管理退出")
                break
    
    def _handle_a_stock(self):
        """处理A股数据管理"""
        while True:
            try:
                print("🔄 正在统计数据状态...")
                data_type_choice = self.cli.show_a_stock_menu()
                
                if data_type_choice == "back":
                    break
                elif data_type_choice == "stock_list":
                    self._handle_stock_list()
                elif data_type_choice == "basic_info":
                    self._handle_basic_info()
                elif data_type_choice == "kline_data":
                    self._handle_kline_data()
                elif data_type_choice == "financial_abstract":
                    self._handle_financial_abstract()
                elif data_type_choice is None:
                    # 无效选择，继续循环
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 返回资产选择")
                break
    
    def _handle_stock_list(self):
        """处理股票清单"""
        choice = self.cli.show_stock_list_menu()
        
        if choice == "update":
            try:
                print("\n🔄 正在获取股票清单...")
                stock_list_data = self.a_stock_fetcher.get_stock_list()
                
                if stock_list_data:
                    print("🔄 正在写入数据库...")
                    count = self.db_writer.write_stock_list(stock_list_data)
                    print(f"✅ 股票清单更新完成！共写入 {count} 只股票")
                else:
                    print("❌ 获取股票清单失败")
            except Exception as e:
                logger.error(f"股票清单更新失败: {e}")
                print(f"❌ 更新失败: {e}")
        
        input("\n按回车键继续...")
    
    def _handle_basic_info(self):
        """处理基本信息"""
        # 需要先有股票清单
        if not self._has_stock_list():
            print("\n❗ 请先更新股票清单（stock_list），再进行基本信息下载。")
            input("按回车键返回上级菜单...")
            return
        # 基本信息只使用固定API (ak.stock_individual_info_em)
        options = self.cli.show_basic_info_menu()
        
        if options["action"] == "back":
            return
        elif options["action"] == "cancel" or options["action"] == "invalid":
            print("❌ 操作已取消")
            input("按回车键返回上级菜单...")
            return
        elif options["action"] == "full_download":
            self._process_basic_info_download(resume=False)
        elif options["action"] == "resume_download":
            self._process_basic_info_download(resume=True)
        elif options["action"] == "specific_download":
            filtered = self._filter_codes_in_stock_list(options["codes"], label="基本信息")
            if not filtered:
                input("按回车键返回上级菜单...")
                return
            self._process_basic_info_download(resume=False, specific_codes=filtered)
    
    def _handle_kline_data(self):
        """处理K线数据"""
        # 需要先有股票清单
        if not self._has_stock_list():
            print("\n❗ 请先更新股票清单（stock_list），再进行K线数据下载。")
            input("按回车键返回上级菜单...")
            return
        # 先显示API选择
        api_info = self.a_stock_fetcher.get_api_info()
        current_api = self.a_stock_fetcher.preferred_api
        
        selected_api = self.cli.show_api_selection_menu(api_info, current_api)
        if selected_api == "back":
            return
        if selected_api and selected_api != current_api:
            self.a_stock_fetcher.set_preferred_api(selected_api)
        
        # 显示状态和选项
        options = self.cli.show_kline_menu()
        
        if options["action"] == "back":
            return
        elif options["action"] == "cancel" or options["action"] == "invalid":
            print("❌ 操作已取消")
            input("按回车键返回上级菜单...")
            return
        elif options["action"] == "full_download":
            self._process_kline_download(resume=False)
        elif options["action"] == "resume_download":
            self._process_kline_download(resume=True)
        elif options["action"] == "specific_download":
            filtered = self._filter_codes_in_stock_list(options["codes"], label="K线数据")
            if not filtered:
                input("按回车键返回上级菜单...")
                return
            self._process_kline_download(resume=False, specific_codes=filtered)
    

    def _handle_financial_abstract(self):
        """处理财务摘要"""
        # 需要先有股票清单
        if not self._has_stock_list():
            print("\n❗ 请先更新股票清单（stock_list），再进行财务摘要下载。")
            input("按回车键返回上级菜单...")
            return
        
        options = self.cli.show_financial_abstract_menu()
        
        if options and options["action"] in ["update", "update_all", "resume_download"]:
            try:
                if options["action"] == "update":
                    codes = self._filter_codes_in_stock_list(options["codes"], label="财务摘要")
                elif options["action"] == "resume_download":
                    codes = self._get_missing_financial_abstract_codes()
                else:  # update_all
                    codes = self._get_all_stock_codes()
                
                if not codes:
                    if options["action"] == "resume_download":
                        print("✅ 所有股票的财务摘要数据已完整，无需补全。")
                    input("按回车键返回上级菜单...")
                    return
                
                # 显示不同的提示信息
                if options["action"] == "update":
                    print(f"\n🔄 下载指定 {len(codes)} 只股票的财务摘要...")
                elif options["action"] == "resume_download":
                    print(f"\n🔄 补全缺失的 {len(codes)} 只股票财务摘要...")
                else:  # update_all
                    print(f"\n🔄 重新下载全部 {len(codes)} 只股票的财务摘要...")
                
                success_count = 0
                for i, code in enumerate(codes, 1):
                    try:
                        print(f"🔄 [{i}/{len(codes)}] 正在处理股票 {code}...")
                        
                        # 获取股票名称
                        stock_name = self._get_stock_name(code)
                        
                        # 获取财务摘要数据
                        df = self.a_stock_fetcher.get_financial_abstract(code)
                        
                        if df is not None and len(df) > 0:
                            # 写入SQLite数据库
                            record_count = self.db_writer.write_financial_abstract(code, stock_name, df)
                            if record_count > 0:
                                success_count += 1
                                print(f"✅ [{i}/{len(codes)}] 股票 {code} 财务摘要获取成功 ({record_count}条记录)")
                            else:
                                print(f"❌ [{i}/{len(codes)}] 股票 {code} 财务摘要写入失败")
                        else:
                            print(f"❌ [{i}/{len(codes)}] 股票 {code} 财务摘要获取失败")
                                    
                    except Exception as e:
                        print(f"❌ [{i}/{len(codes)}] 股票 {code} 处理失败: {e}")
                        logger.error(f"处理股票 {code} 财务摘要失败: {e}")
                
                print(f"✅ 财务摘要下载完成！成功处理 {success_count} 只股票")
            except Exception as e:
                print(f"❌ 下载失败: {e}")
        
        input("\n按回车键继续...")

    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT stock_name FROM stock_list WHERE stock_code = ?", (stock_code,))
                result = cursor.fetchone()
                return result[0] if result else stock_code
        except Exception:
            return stock_code

    def _has_stock_list(self) -> bool:
        """是否已有股票清单数据"""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.execute("SELECT COUNT(*) FROM stock_list")
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def _filter_codes_in_stock_list(self, codes: list, label: str = "操作") -> list:
        """过滤用户指定的股票代码，确保都在stock_list中，提示缺失项"""
        import sqlite3
        if not codes:
            return []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                placeholders = ",".join(["?"] * len(codes))
                cursor = conn.execute(
                    f"SELECT stock_code FROM stock_list WHERE stock_code IN ({placeholders})",
                    codes
                )
                existing = {row[0] for row in cursor.fetchall()}
        except Exception:
            existing = set()
        missing = [c for c in codes if c not in existing]
        if missing:
            print(f"⚠️ 以下代码未在股票清单中，已忽略: {missing}")
        if not existing:
            print(f"❗ 未找到有效的股票代码用于{label}，请先更新股票清单或检查输入。")
            return []
        return sorted(existing)
    
    def _process_basic_info_download(self, resume=True, specific_codes=None):
        """处理基本信息下载"""
        try:
            if specific_codes:
                # 过滤有效股票代码
                valid_codes = [code for code in specific_codes if code.startswith(('6', '3', '0'))]
                stock_codes = valid_codes
                print(f"\n🔄 下载 {len(stock_codes)} 只指定股票的基本信息...")
            else:
                stock_codes = self._get_all_stock_codes()
                if resume:
                    stock_codes = self._get_missing_basic_info_codes(stock_codes)
                    if not stock_codes:
                        print("✅ 所有股票的基本信息都已完整，无需更新")
                        input("按回车键继续...")
                        return
                print(f"\n🔄 下载 {len(stock_codes)} 只股票的基本信息...")
            
            # 并发处理
            success_count = 0
            total_count = len(stock_codes)
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future_to_stock = {
                    executor.submit(self._process_single_basic_info, code): code 
                    for code in stock_codes
                }
                
                for i, future in enumerate(as_completed(future_to_stock), 1):
                    stock_code = future_to_stock[future]
                    try:
                        if future.result():
                            success_count += 1
                        
                        if i % 10 == 0:
                            progress_pct = (i / total_count) * 100
                            success_rate = (success_count / i) * 100
                            print(f"\n📊 【基本信息下载进度】")
                            print(f"   进度: {i}/{total_count} ({progress_pct:.1f}%) | 成功: {success_count} ({success_rate:.1f}%)")
                            print("   " + "█" * int(progress_pct // 5) + "░" * (20 - int(progress_pct // 5)))
                            
                    except Exception as e:
                        logger.warning(f"处理股票 {stock_code} 基本信息失败: {e}")
            
            print(f"\n✅ 基本信息下载完成！成功更新 {success_count} 只股票")
        except Exception as e:
            logger.error(f"基本信息下载失败: {e}")
            print(f"❌ 下载失败: {e}")
        
        input("按回车键继续...")
    
    def _process_kline_download(self, resume=True, specific_codes=None):
        """处理K线数据下载"""
        try:
            if specific_codes:
                # 过滤有效股票代码
                valid_codes = [code for code in specific_codes if code.startswith(('6', '3', '0'))]
                stock_codes = valid_codes
                print(f"\n🔄 下载 {len(stock_codes)} 只指定股票的K线数据...")
            else:
                stock_codes = self._get_all_stock_codes()
                if resume:
                    stock_codes = self._get_missing_kline_codes(stock_codes)
                    if not stock_codes:
                        print("✅ 所有股票的K线数据都已最新，无需更新")
                        input("按回车键继续...")
                        return
                print(f"\n🔄 下载 {len(stock_codes)} 只股票的K线数据...")
            
            # 并发处理
            success_count = 0
            total_records = 0
            total_count = len(stock_codes)
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future_to_stock = {
                    executor.submit(self._process_single_kline, code): code 
                    for code in stock_codes
                }
                
                for i, future in enumerate(as_completed(future_to_stock), 1):
                    stock_code = future_to_stock[future]
                    try:
                        record_count = future.result()
                        if record_count > 0:
                            success_count += 1
                            total_records += record_count
                        
                        if i % 5 == 0:
                            progress_pct = (i / total_count) * 100
                            success_rate = (success_count / i) * 100 if i > 0 else 0
                            avg_records = total_records // success_count if success_count > 0 else 0
                            print(f"\n📈 【K线数据下载进度】")
                            print(f"   进度: {i}/{total_count} ({progress_pct:.1f}%) | 成功: {success_count} ({success_rate:.1f}%)")
                            print(f"   总记录: {total_records:,} 条 | 平均: {avg_records} 条/股")
                            print("   " + "█" * int(progress_pct // 5) + "░" * (20 - int(progress_pct // 5)))
                            
                    except Exception as e:
                        logger.warning(f"处理股票 {stock_code} K线数据失败: {e}")
            
            print(f"\n✅ K线数据下载完成！成功更新 {success_count} 只股票，总记录数: {total_records:,}")
        except Exception as e:
            logger.error(f"K线数据下载失败: {e}")
            print(f"❌ 下载失败: {e}")
        
        input("按回车键继续...")
    
    def _process_single_basic_info(self, stock_code: str) -> bool:
        """处理单只股票基本信息"""
        try:
            basic_info = self.a_stock_fetcher.get_basic_info(stock_code)
            if basic_info:
                return self.db_writer.write_basic_info(stock_code, basic_info)
        except Exception as e:
            logger.warning(f"处理股票 {stock_code} 基本信息失败: {e}")
        return False
    
    def _process_single_kline(self, stock_code: str) -> int:
        """处理单只股票K线数据"""
        try:
            start_date, end_date = self.a_stock_fetcher.get_stock_date_range(stock_code)
            kline_data = self.a_stock_fetcher.get_kline_data(stock_code, start_date, end_date)
            
            if kline_data:
                return self.db_writer.write_kline_data(stock_code, kline_data, start_date, end_date)
        except Exception as e:
            logger.warning(f"处理股票 {stock_code} K线数据失败: {e}")
        return 0
    
    def _get_all_stock_codes(self) -> list:
        """获取所有股票代码"""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.execute("SELECT stock_code FROM stock_list ORDER BY stock_code")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"获取股票代码列表失败: {e}")
            return []
    
    def _get_missing_basic_info_codes(self, all_codes: list) -> list:
        """获取缺少基本信息的股票代码"""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.execute("""
                    SELECT sl.stock_code
                    FROM stock_list sl 
                    LEFT JOIN stock_basic_info sbi ON sl.stock_code = sbi.stock_code 
                    WHERE sbi.stock_code IS NULL AND sl.stock_code IN ({})
                """.format(','.join('?' * len(all_codes))), all_codes)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"获取缺失基本信息股票代码失败: {e}")
            return []
    
    def _get_missing_kline_codes(self, all_codes: list) -> list:
        """获取需要更新K线数据的股票代码"""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.execute("""
                    SELECT sl.stock_code
                    FROM stock_list sl 
                    LEFT JOIN stock_daily_kline sdk ON sl.stock_code = sdk.stock_code 
                    WHERE sl.stock_code IN ({})
                    GROUP BY sl.stock_code
                    HAVING COUNT(sdk.stock_code) = 0 
                       OR MAX(sdk.trade_date) < date('now', '-7 days')
                """.format(','.join('?' * len(all_codes))), all_codes)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"获取需要更新K线数据的股票代码失败: {e}")
            return []
    
    def _get_missing_financial_abstract_codes(self) -> list:
        """获取缺失财务摘要的股票代码"""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.execute("""
                    SELECT sl.stock_code, sl.stock_name
                    FROM stock_list sl 
                    LEFT JOIN stock_financial_abstract sfa ON sl.stock_code = sfa.stock_code 
                    WHERE sfa.stock_code IS NULL
                    ORDER BY sl.stock_code
                """)
                codes = [row[0] for row in cursor.fetchall()]
                logger.info(f"找到 {len(codes)} 只缺失财务摘要的股票")
                return codes
        except Exception as e:
            logger.warning(f"获取缺失财务摘要的股票代码失败: {e}")
            return []