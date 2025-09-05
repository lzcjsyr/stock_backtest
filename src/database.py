"""
数据库操作模块 - SQLite多文件数据库
"""
from .sqlite_database import SQLiteStockDatabase

# 兼容性别名，保持与现有代码的兼容性
StockDatabase = SQLiteStockDatabase

if __name__ == "__main__":
    db = StockDatabase()
    info = db.get_available_dates()
    if info is not None and info['total_records'] > 0:
        print(f"📊 数据库状态: {info['start_date']} 到 {info['end_date']}, 共 {info['total_records']} 条记录")
    else:
        print("📊 数据库为空，需要先获取数据")