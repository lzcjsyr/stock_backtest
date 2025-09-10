#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import logging
import pymongo

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """数据库初始化器 - 支持多资产类型"""
    
    def __init__(self, base_dir: str, asset_type: str = "a_stock"):
        self.base_dir = base_dir
        self.asset_type = asset_type
        self.data_dir = os.path.join(base_dir, "data")
        
        # 为每种资产类型创建独立的文件夹
        self.asset_data_dir = os.path.join(self.data_dir, asset_type)
        
        # 数据库文件存放在对应的资产文件夹中
        self.db_path = os.path.join(self.asset_data_dir, f"{asset_type}_data.db")
        
        # MongoDB连接信息 - 为不同资产类型使用不同的数据库
        self.mongo_host = "localhost"
        self.mongo_port = 27017
        self.mongo_db_name = f"{asset_type}_financial_data"
        # MongoDB数据文件也存储在对应资产文件夹（通过配置文件实现）
        self.mongo_data_path = os.path.join(self.asset_data_dir, "mongodb")
        self.mongo_client = None
        self.mongo_available = False
        
        # 支持的资产类型配置
        self.asset_configs = {
            "a_stock": {
                "display_name": "A股"
            },
            "hk_stock": {
                "display_name": "港股"
            },
            "us_stock": {
                "display_name": "美股"
            },
            "fund": {
                "display_name": "基金"
            }
        }
        
        self.ensure_data_dir()
        # 延后初始化 MongoDB，按需连接/启动
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.asset_data_dir, exist_ok=True)
        # 创建MongoDB数据目录
        os.makedirs(self.mongo_data_path, exist_ok=True)
    
    def init_mongodb(self) -> bool:
        """尝试建立到 MongoDB 的连接（不自启动）。"""
        try:
            self.mongo_client = pymongo.MongoClient(
                host=self.mongo_host,
                port=self.mongo_port,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            self.mongo_client.admin.command('ping')
            self.mongo_available = True
            logger.info(f"MongoDB已就绪: {self.mongo_host}:{self.mongo_port}")
            return True
        except Exception as e:
            self.mongo_available = False
            self.mongo_client = None
            logger.info(f"MongoDB未就绪: {e}")
            return False

    def ensure_mongodb_running(self, max_wait_seconds: int = 20) -> bool:
        """确保 MongoDB 可用：若未运行则尝试启动并等待就绪。

        优先顺序：Homebrew 服务 -> 本机 mongod 直接启动。
        返回 True 表示可用，False 表示不可用。
        """
        import shutil
        import subprocess
        import time

        # 已可用则直接返回
        if self.mongo_available and self.mongo_client is not None:
            return True

        # 先尝试直接连接（可能系统级服务已在运行）
        if self.init_mongodb():
            return True

        start_methods = []
        if shutil.which('brew') is not None:
            start_methods.append(('brew', ['brew', 'services', 'start', 'mongodb-community']))

        # 直接使用 mongod --fork
        mongod_path = shutil.which('mongod')
        if mongod_path is not None:
            log_path = os.path.join(self.mongo_data_path, 'mongod.log')
            start_methods.append(('mongod', [
                mongod_path,
                '--dbpath', self.mongo_data_path,
                '--port', str(self.mongo_port),
                '--bind_ip', '127.0.0.1',
                '--logpath', log_path,
                '--fork'
            ]))

        for method, cmd in start_methods:
            try:
                logger.info(f"尝试启动MongoDB（{method}）...")
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            except Exception as e:
                logger.info(f"启动命令失败（{method}）: {e}")
                continue

            # 启动后轮询等待就绪
            deadline = time.time() + max_wait_seconds
            while time.time() < deadline:
                if self.init_mongodb():
                    return True
                time.sleep(1)

        logger.warning("MongoDB不可用：启动尝试失败或未安装。财务报表功能将不可用。")
        return False
    
    def get_mongo_client(self):
        """获取MongoDB客户端"""
        return self.mongo_client if self.mongo_available else None
    
    def get_mongo_db(self):
        """获取MongoDB数据库"""
        if self.mongo_available:
            return self.mongo_client[self.mongo_db_name]
        return None
    
    def init_sqlite_database(self):
        """初始化SQLite数据库"""
        asset_config = self.asset_configs.get(self.asset_type, self.asset_configs["a_stock"])
        
        with sqlite3.connect(self.db_path) as conn:
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            if self.asset_type == "a_stock":
                # A股数据表结构
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_list (
                        stock_code TEXT PRIMARY KEY,
                        stock_name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_basic_info (
                        stock_code TEXT PRIMARY KEY REFERENCES stock_list(stock_code) ON UPDATE CASCADE ON DELETE CASCADE,
                        stock_name TEXT,
                        total_share REAL,
                        float_share REAL,
                        total_market_value REAL,
                        float_market_value REAL,
                        industry TEXT,
                        list_date TEXT,
                        latest_price REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_daily_kline (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stock_code TEXT NOT NULL REFERENCES stock_list(stock_code) ON UPDATE CASCADE ON DELETE CASCADE,
                        trade_date DATE NOT NULL,
                        open_price REAL NOT NULL,
                        close_price REAL NOT NULL,
                        high_price REAL NOT NULL,
                        low_price REAL NOT NULL,
                        volume INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(stock_code, trade_date)
                    )
                """)
                
                # 确保财务摘要表存在（兼容现有数据库）
                self._ensure_financial_abstract_table(conn)
                
                # 创建索引
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_date ON stock_daily_kline(trade_date)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_industry ON stock_basic_info(industry)")
                
            elif self.asset_type == "hk_stock":
                # 港股数据表结构（待实现）
                pass
            
            elif self.asset_type == "us_stock":
                # 美股数据表结构（待实现）
                pass
            
            elif self.asset_type == "fund":
                # 基金数据表结构（待实现）
                pass
            
            conn.commit()
            logger.info(f"{asset_config['display_name']} SQLite数据库初始化完成")
            logger.info(f"数据库文件: {self.db_path}")
            logger.info(f"资产数据目录: {self.asset_data_dir}")
    
    def _ensure_financial_abstract_table(self, conn):
        """确保财务摘要表存在（兼容现有数据库）"""
        try:
            # 检查表是否存在
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='stock_financial_abstract'"
            )
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                logger.info("创建财务摘要表...")
                self._create_financial_abstract_table(conn)
                logger.info("✅ 财务摘要表创建成功")
            else:
                logger.debug("财务摘要表已存在，跳过创建")
                
        except Exception as e:
            logger.error(f"财务摘要表管理失败: {e}")
            raise

    def _create_financial_abstract_table(self, conn):
        """创建财务摘要表和索引"""
        conn.execute('''
            CREATE TABLE stock_financial_abstract (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                category TEXT NOT NULL,
                indicator TEXT NOT NULL,
                report_date TEXT NOT NULL,
                value REAL,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_code, indicator, report_date),
                FOREIGN KEY (stock_code) REFERENCES stock_list(stock_code)
            )
        ''')
        
        # 创建索引
        indexes = [
            'CREATE INDEX idx_financial_stock_code ON stock_financial_abstract(stock_code)',
            'CREATE INDEX idx_financial_report_date ON stock_financial_abstract(report_date)', 
            'CREATE INDEX idx_financial_indicator ON stock_financial_abstract(indicator)',
            'CREATE INDEX idx_financial_category ON stock_financial_abstract(category)'
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def get_db_path(self):
        """获取数据库路径"""
        return self.db_path