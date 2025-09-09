# 📈 股票回测系统

基于AKShare的量化投资策略回测平台，采用SQLite多文件存储架构，支持策略开发、回测分析和结果可视化。

## 🎯 项目特性

- 💻 **命令行界面**: 简洁的CLI交互，易于操作和自动化
- 📡 **数据管理**: 基于AKShare获取A股实时数据，支持多数据源扩展
- 🗄️ **高效存储**: SQLite多文件架构，价格数据和基本信息分离存储
- 📊 **策略框架**: 标准化策略开发模板，支持快速策略实现
- 📈 **专业图表**: HTML+Chart.js技术生成高质量净值图表
- 📋 **完整报告**: Excel详细数据 + PNG图表 + README文档

## 🏗️ 项目架构

```
股票回测系统/
├── main.py                    # 主程序入口 - CLI交互界面
├── data_downloader/           # 数据下载管理模块
│   ├── router.py             # 数据路由和菜单管理
│   ├── a_stock.py            # A股数据下载器
│   ├── db_writer.py          # 数据库写入管理
│   └── cli_interface.py      # 命令行交互界面
├── strategies/                # 量化策略模块
│   └── low_ttm_pe_strategy.py # 低TTM PE策略(样板)
├── src/                       # 核心功能模块
│   ├── database.py           # 数据库统一接口
│   ├── sqlite_database.py    # SQLite多文件数据库
│   └── visualizer.py         # 图表可视化引擎
├── data/                      # 数据存储目录
│   ├── stock_basic.db        # 股票基本信息数据库
│   ├── stock_prices.db       # 股票价格数据库
│   └── stock_metadata.db     # 元数据配置数据库
├── assets/js/                 # 前端资源文件
│   └── (Chart.js相关库)       # 图表生成依赖
├── results/                   # 策略回测结果
│   └── [策略名_时间戳]/       # 每次回测的完整结果
└── requirements.txt           # Python依赖包列表
```

## 💡 系统设计

### 程序运行流程

1. **启动系统**: 运行 `python main.py` 进入命令行界面
2. **功能选择**: 
   - **数据管理**: 进入多资产数据下载和管理
   - **策略回测**: 选择已开发的量化策略进行回测
3. **数据管理流程**: 选择资产类型 → 选择数据类型 → 自动下载更新
4. **策略回测流程**: 选择策略 → 自动运行回测 → 生成完整报告
5. **结果输出**: 回测结果自动保存到 `results/[策略名_时间戳]/` 目录

## 📊 数据存储架构

### SQLite多文件存储设计

采用 **SQLite多文件存储架构**，按数据类型分离存储，提升查询性能和维护便利性：

- **stock_basic.db**: 股票基本信息（代码、名称、行业、上市日期等）
- **stock_prices.db**: 股票价格数据（日K线数据，支持高频查询）
- **stock_metadata.db**: 系统元数据（数据状态、配置信息等）

### 数据表结构设计

#### 1. 股票基本信息表 (stock_info)

**存储位置**: `data/stock_basic.db`

**数据源**: AKShare股票基本信息接口

```sql
CREATE TABLE stock_info (
    stock_code TEXT PRIMARY KEY,        -- 股票代码 (6位)
    stock_name TEXT NOT NULL,           -- 股票简称
    market TEXT DEFAULT 'A',            -- 市场标识
    list_date DATE,                     -- 上市日期
    industry TEXT,                      -- 所属行业
    concept TEXT,                       -- 概念板块
    is_active INTEGER DEFAULT 1,        -- 是否活跃 (1:活跃, 0:停牌)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. 股票价格数据表 (stock_daily_prices)

**存储位置**: `data/stock_prices.db`

**数据源**: AKShare日K线数据（前复权）

```sql
CREATE TABLE stock_daily_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,           -- 股票代码
    trade_date DATE NOT NULL,           -- 交易日期
    open_price REAL NOT NULL,           -- 开盘价
    high_price REAL NOT NULL,           -- 最高价
    low_price REAL NOT NULL,            -- 最低价
    close_price REAL NOT NULL,          -- 收盘价
    volume INTEGER NOT NULL,            -- 成交量
    amount REAL NOT NULL,               -- 成交额
    pct_change REAL,                    -- 涨跌幅(%)
    price_change REAL,                  -- 涨跌额
    turnover_rate REAL,                 -- 换手率(%)
    amplitude REAL,                     -- 振幅(%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)      -- 防重复约束
);
```

#### 3. 系统元数据表 (data_status)

**存储位置**: `data/stock_metadata.db`

**用途**: 追踪数据更新状态和系统配置

```sql
CREATE TABLE data_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,           -- 表名
    stock_code TEXT,                    -- 股票代码(可选)
    start_date DATE,                    -- 数据起始日期
    end_date DATE,                      -- 数据截止日期
    record_count INTEGER DEFAULT 0,     -- 记录数量
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'       -- 数据状态
);
```

### 数据库索引设计

为提升查询性能，系统为关键字段创建了适当的索引：

#### SQLite索引策略

```sql
-- 股票基本信息表索引
CREATE INDEX idx_industry ON stock_info(industry);
CREATE INDEX idx_is_active ON stock_info(is_active);

-- 股票价格数据表索引  
CREATE INDEX idx_stock_code ON stock_daily_prices(stock_code);
CREATE INDEX idx_trade_date ON stock_daily_prices(trade_date);
CREATE INDEX idx_stock_date ON stock_daily_prices(stock_code, trade_date);
CREATE INDEX idx_close_price ON stock_daily_prices(close_price);
```

## 🚀 快速开始

### 环境准备

#### 1. Python环境
```bash
# 确保Python版本 >= 3.8
python --version
```

#### 2. 安装依赖包
```bash
# 安装所有依赖
pip install -r requirements.txt

# 如果需要图表生成功能，需要安装浏览器
playwright install chromium
```

### 系统启动

```bash
# 启动主程序
python main.py
```

### 首次使用流程

1. **启动系统** → 选择 "1. 📡 数据管理"
2. **选择资产类型** → "A股数据" 
3. **下载基础数据** → 选择要下载的数据类型（股票列表、价格数据等）
4. **等待下载完成** → 系统自动保存到本地数据库
5. **运行策略回测** → 返回主菜单选择 "2. 📊 策略回测"
6. **查看结果** → 回测报告自动保存到 `results/` 目录

## 📊 量化策略开发

### 现有策略

#### 1. 低TTM PE轮动策略 (`low_ttm_pe_strategy.py`)

**策略描述**: 每月从沪深主板市值≥100亿的股票中，按TTM PE升序排列，选择前10只股票等权重持仓

**核心特点**:
- 选股范围: 沪深主板(6开头+0开头)，排除创业板和科创板
- 市值过滤: 最低市值100亿元，确保流动性
- TTM PE计算: 基于滚动12个月EPS，避免季节性影响
- 调仓频率: 月度调仓，平衡收益与成本
- 权重分配: 等权重配置，降低个股风险

**策略参数**:
- `MIN_MARKET_CAP`: 最低市值要求(亿元)，默认100
- `STOCK_COUNT`: 选股数量，默认10只
- `TRANSACTION_COST`: 交易手续费率，默认万1
- `START_DATE`/`END_DATE`: 回测时间范围

**回测报告**:
- Excel详细数据表格
- HTML高质量净值图表
- 完整策略说明文档

### 策略扩展能力

系统设计支持快速添加新策略:
- 标准化策略接口
- 统一的回测框架
- 自动化报告生成
- 参数化配置支持

### 添加新策略步骤

1. 在 `strategies/` 目录创建新的 `.py` 文件
2. 实现 `run_backtest()` 函数
3. 使用统一的数据库接口获取数据
4. 调用回测框架生成报告
5. 通过主程序菜单直接运行

## 🛠️ 技术架构

### 核心技术栈
- **数据源**: AKShare - A股数据获取
- **存储**: SQLite多文件架构 - 高性能本地存储
- **数据处理**: pandas + numpy - 高效数据分析
- **可视化**: HTML + Chart.js - 专业级图表
- **表格输出**: openpyxl - Excel详细报告
- **截图生成**: Playwright - 高质量图像输出

### 开发环境要求

```bash
# Python版本
Python >= 3.8

# 核心依赖
akshare >= 1.12.0      # 数据获取
pandas >= 2.0.0        # 数据处理
numpy >= 1.24.0        # 数值计算
matplotlib >= 3.7.0    # 基础绘图
playwright >= 1.40.0   # 浏览器自动化
openpyxl >= 3.1.0      # Excel处理
```

## 📁 回测结果结构

每次运行策略回测会在 `results/` 目录下生成完整的结果文件夹:

```
results/
└── 主板低TTM_PE策略_0908_1425/
    ├── backtest_results.xlsx    # Excel详细数据
    │   ├── Strategy_Overview    # 策略概览工作表
    │   └── Stock_Selection      # 选股详情工作表
    ├── net_value_chart.png      # 高质量净值走势图
    └── README.md                # 策略回测报告
```

## 🔄 系统扩展规划

### 数据源扩展
- 港股数据支持
- 美股数据支持  
- 基金数据支持
- 指数数据支持

### 策略类型扩展
- 技术分析策略
- 多因子策略
- 行业轮动策略
- 量化套利策略

### 功能增强
- 策略组合回测
- 风险指标分析
- 基准比较分析
- 实盘交易接口

## ⚠️ 免责声明

本系统仅供学习研究使用，所有回测结果不构成投资建议。
历史业绩不代表未来表现，投资有风险，决策需谨慎。

## 📞 技术支持

如有问题或建议，欢迎通过以下方式联系:
- 创建 Issue 反馈问题
- 提交 Pull Request 贡献代码

---

*📊 用数据驱动投资决策，让量化分析成为您的投资利器！*
