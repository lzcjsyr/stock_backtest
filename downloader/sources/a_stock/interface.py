#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CLIInterface:
    """CLI交互界面"""
    
    def __init__(self, db_path: str, db_init=None):
        self.db_path = db_path
        self.db_init = db_init
    
    def show_asset_selection_menu(self) -> Optional[str]:
        """显示资产选择菜单"""
        try:
            print("\n🎯 数据管理 - 资产类别选择")
            print("=" * 50)
            print("请选择要管理的资产类别:")
            print()
            
            # 已实现的资产
            print("1. A股 - 沪深交易所股票数据")
            
            # 规划中的资产
            print("2. 港股 - 香港交易所股票数据 (规划中)")
            print("3. 美股 - 美国交易所股票数据 (规划中)")
            print("4. 公募基金 - 公募基金数据 (规划中)")
            print("5. 私募基金 - 私募基金数据 (规划中)")
            print("6. 返回主菜单")
            
            choice = input(f"\n请选择资产类别 (1-6): ").strip()
            choice_num = int(choice)
            
            if choice_num == 1:
                return "a_stock"
            elif 2 <= choice_num <= 5:
                print("❌ 该功能尚未实现，敬请期待")
                input("按回车键继续...")
                return None
            elif choice_num == 6:
                return "exit"
            else:
                print("❌ 无效选择")
                input("按回车键继续...")
                return None
                
        except ValueError:
            print("❌ 请输入有效数字")
            input("按回车键继续...")
            return None
        except KeyboardInterrupt:
            print("\n👋 返回主菜单")
            return "exit"
    
    def show_a_stock_menu(self) -> Optional[str]:
        """显示A股数据管理菜单"""
        try:
            # 获取状态摘要
            status_summary = self._get_a_stock_status()
            
            print(f"\n📈 A股数据管理")
            print("=" * 50)
            print(f"描述: 沪深交易所股票数据")
            
            if status_summary:
                print(f"\n📊 数据状态概览:")
                for key, value in status_summary.items():
                    print(f"   {key}: {value:,}")
            
            print(f"\n数据类型:")
            print("1. 股票清单")
            print("2. 股票基本信息")
            print("3. 日K线数据")
            print("4. 财务摘要")
            print("5. 返回上级菜单")
            
            choice = input(f"\n请选择数据类型 (1-5): ").strip()
            choice_num = int(choice)
            
            if choice_num == 1:
                return "stock_list"
            elif choice_num == 2:
                return "basic_info"
            elif choice_num == 3:
                return "kline_data"
            elif choice_num == 4:
                return "financial_abstract"
            elif choice_num == 5:
                return "back"
            else:
                print("❌ 无效选择")
                input("按回车键继续...")
                return None
                
        except ValueError:
            print("❌ 请输入有效数字")
            input("按回车键继续...")
            return None
        except KeyboardInterrupt:
            print("\n👋 返回上级菜单")
            return "back"
    
    def show_api_selection_menu(self, api_info: dict, current_api: str) -> Optional[str]:
        """显示API选择菜单"""
        try:
            print(f"\n📡 选择API数据源")
            print("=" * 50)
            
            # 简化的API名称映射
            api_names = {
                "stock_zh_a_hist": "东方财富",
                "stock_zh_a_daily": "新浪财经",
                "stock_zh_a_hist_tx": "腾讯证券"
            }
            
            api_list = list(api_info.keys())
            for i, api_name in enumerate(api_list, 1):
                display_name = api_names.get(api_name, api_name)
                print(f"{i}. {display_name}")
            
            print(f"{len(api_list) + 1}. 返回上级菜单")
            
            choice = input(f"\n请选择API数据源 (1-{len(api_list) + 1}): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(api_list):
                selected_api = api_list[choice_num - 1]
                display_name = api_names.get(selected_api, selected_api)
                print(f"✅ API已设置为: {display_name}")
                return selected_api
            elif choice_num == len(api_list) + 1:
                print("↩️ 返回上级菜单")
                return "back"
            else:
                print("❌ 无效选择")
                return None
                
        except ValueError:
            print("❌ 请输入有效数字")
            return None
        except Exception as e:
            print(f"❌ 设置失败: {e}")
            return None
    
    def show_stock_list_menu(self) -> Optional[str]:
        """显示股票清单管理菜单"""
        print(f"\n📋 股票清单管理")
        print("=" * 30)
        print("1. 更新股票清单")
        print("2. 返回")
        
        choice = input("\n请选择操作 (1-2): ").strip()
        if choice == "1":
            return "update"
        elif choice == "2":
            return "back"
        else:
            print("❌ 无效选择")
            return None
    
    def show_basic_info_menu(self) -> dict:
        """显示基本信息管理菜单"""
        status = self._get_download_status()
        
        print(f"\n📊 股票基本信息状态")
        print("=" * 50)
        print(f"数据源: 东方财富 (ak.stock_individual_info_em)")
        print(f"总股票数量: {status['total_stocks']}")
        print(f"基本信息完整: {status['basic_info_complete']} ({status['basic_info_complete']/status['total_stocks']*100:.1f}%)")
        print(f"基本信息缺失: {status['basic_info_missing']} ({status['basic_info_missing']/status['total_stocks']*100:.1f}%)")
        
        if status['basic_info_missing'] > 0:
            print(f"缺少基本信息的股票 (前10个): {[stock[0] for stock in status['missing_basic_info_stocks'][:10]]}")
        
        return self._show_download_options("基本信息")
    
    def show_kline_menu(self) -> dict:
        """显示K线数据管理菜单"""
        status = self._get_download_status()
        total_need_update = status['kline_missing'] + status['kline_outdated']
        
        print(f"\n📈 日K线数据状态")
        print("=" * 50)
        print(f"总股票数量: {status['total_stocks']}")
        print(f"K线数据完整: {status['kline_complete']} ({status['kline_complete']/status['total_stocks']*100:.1f}%)")
        print(f"K线数据缺失: {status['kline_missing']} ({status['kline_missing']/status['total_stocks']*100:.1f}%)")
        print(f"K线数据过期: {status['kline_outdated']} ({status['kline_outdated']/status['total_stocks']*100:.1f}%)")
        print(f"需要更新的股票: {total_need_update} 只")
        
        if status['kline_outdated'] > 0:
            print(f"K线数据过期的股票 (前10个): {[stock[0] for stock in status['outdated_kline_stocks'][:10]]}")
        
        if status['kline_missing'] > 0:
            print(f"缺少K线数据的股票 (前10个): {[stock[0] for stock in status['missing_kline_stocks'][:10]]}")
        
        return self._show_download_options("日K线数据")
    
    
    def show_financial_abstract_menu(self) -> Optional[str]:
        """显示财务摘要管理菜单"""
        # 获取缺失统计
        missing_count = self._get_missing_financial_abstract_count()
        
        print(f"\n💰 财务摘要管理")
        print("=" * 30)
        print("财务摘要包含80个核心财务指标，涵盖7大类别")
        if missing_count > 0:
            print(f"📊 缺失财务摘要: {missing_count:,} 只股票")
        print("1. 更新指定股票财务摘要")
        print("2. 补全缺失的财务摘要")
        print("3. 更新全部财务摘要")
        print("4. 返回")
        
        choice = input("\n请选择操作 (1-4): ").strip()
        if choice == "1":
            codes_input = input("请输入股票代码(多个代码用逗号分隔): ").strip()
            if codes_input:
                codes = [code.strip() for code in codes_input.split(",")]
                return {"action": "update", "codes": codes}
        elif choice == "2":
            return {"action": "resume_download"}
        elif choice == "3":
            return {"action": "update_all"}
        elif choice == "4":
            return {"action": "back"}
        
        return None
    
    def _get_missing_financial_abstract_count(self) -> int:
        """获取缺失财务摘要的股票数量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*)
                    FROM stock_list sl 
                    LEFT JOIN stock_financial_abstract sfa ON sl.stock_code = sfa.stock_code 
                    WHERE sfa.stock_code IS NULL
                """)
                return cursor.fetchone()[0]
        except Exception as e:
            logger.warning(f"获取缺失财务摘要数量失败: {e}")
            return 0
    
    def _show_download_options(self, data_type: str) -> dict:
        """显示下载选项"""
        print("\n下载选项:")
        print("1. 全量重新下载")
        print("2. 补全缺失的数据")
        print("3. 指定股票代码下载")
        print("4. 返回")
        
        choice = input("\n请选择下载方式 (1-4): ").strip()
        
        if choice == "1":
            if data_type == "日K线数据":
                print("⚠️ 警告：这将重新下载所有股票的完整K线数据，可能需要很长时间")
                if input("确认继续? (y/N): ").strip().lower() != 'y':
                    print("❌ 操作已取消")
                    return {"action": "cancel"}
            return {"action": "full_download"}
        elif choice == "2":
            return {"action": "resume_download"}
        elif choice == "3":
            codes_input = input("请输入股票代码(多个代码用逗号分隔): ").strip()
            if codes_input:
                codes = [code.strip() for code in codes_input.split(",")]
                return {"action": "specific_download", "codes": codes}
            return {"action": "cancel"}
        elif choice == "4":
            return {"action": "back"}
        else:
            print("❌ 无效选择")
            return {"action": "invalid"}
    
    def _get_a_stock_status(self) -> dict:
        """获取A股数据状态摘要"""
        try:
            status = self._get_download_status()
            return {
                "股票总数": status.get('total_stocks', 0),
                "基本信息完整": status.get('basic_info_complete', 0),
                "K线数据完整": status.get('kline_complete', 0),
                "财务摘要完整": status.get('financial_complete', 0)
            }
        except Exception:
            return {}
    
    def _get_download_status(self) -> dict:
        """获取详细下载状态"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取总股票数
            cursor = conn.execute("SELECT COUNT(*) FROM stock_list")
            total_stocks = cursor.fetchone()[0]
            
            # 获取已有基本信息的股票数
            cursor = conn.execute("SELECT COUNT(*) FROM stock_basic_info")
            basic_info_count = cursor.fetchone()[0]
            
            # 获取有K线数据的股票数
            cursor = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_daily_kline")
            kline_stocks_count = cursor.fetchone()[0]
            
            # 获取缺少基本信息的股票
            cursor = conn.execute("""
                SELECT sl.stock_code, sl.stock_name 
                FROM stock_list sl 
                LEFT JOIN stock_basic_info sbi ON sl.stock_code = sbi.stock_code 
                WHERE sbi.stock_code IS NULL
                ORDER BY sl.stock_code
            """)
            missing_basic_info = cursor.fetchall()
            
            # 获取缺少K线数据的股票
            cursor = conn.execute("""
                SELECT sl.stock_code, sl.stock_name 
                FROM stock_list sl 
                LEFT JOIN stock_daily_kline sdk ON sl.stock_code = sdk.stock_code 
                WHERE sdk.stock_code IS NULL
                GROUP BY sl.stock_code, sl.stock_name
                ORDER BY sl.stock_code
            """)
            missing_kline = cursor.fetchall()
            
            # 获取K线数据过期的股票（最近30天没有数据）
            cursor = conn.execute("""
                SELECT sl.stock_code, sl.stock_name, 
                       MAX(sdk.trade_date) as last_update
                FROM stock_list sl 
                LEFT JOIN stock_daily_kline sdk ON sl.stock_code = sdk.stock_code 
                WHERE sdk.stock_code IS NOT NULL
                GROUP BY sl.stock_code, sl.stock_name
                HAVING MAX(sdk.trade_date) < date('now', '-30 days')
                ORDER BY sl.stock_code
            """)
            outdated_kline = cursor.fetchall()
            
            # 获取财务摘要数据统计
            financial_count = 0
            try:
                cursor = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_financial_abstract")
                financial_count = cursor.fetchone()[0]
            except Exception as e:
                logger.warning(f"获取财务摘要统计失败: {e}")
            
            return {
                'total_stocks': total_stocks,
                'basic_info_complete': basic_info_count,
                'basic_info_missing': len(missing_basic_info),
                'kline_complete': kline_stocks_count,
                'kline_missing': len(missing_kline),
                'kline_outdated': len(outdated_kline),
                'financial_complete': financial_count,
                'missing_basic_info_stocks': missing_basic_info,
                'missing_kline_stocks': missing_kline,
                'outdated_kline_stocks': outdated_kline
            }