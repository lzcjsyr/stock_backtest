# 📈 股票回测系统

基于 AKShare 的股票策略回测系统，使用 MongoDB + SQLite 混合存储架构，支持多种投资策略回测。提供图形化界面进行数据更新和策略回测。

## 🎯 项目特性

- 🖥️ **图形界面**: 用户友好的GUI界面，轻松操作
- 📡 **数据获取**: 基于 AKShare 获取 A 股数据
- 🗄️ **数据存储**: MongoDB存储财务报表，SQLite存储价格数据
- 📊 **策略回测**: 支持多种投资策略回测
- 📈 **可视化分析**: 生成收益曲线和风险分析图表
- 📋 **详细报告**: 输出完整的回测分析报告

## 🏗️ 系统架构

```
股票回测系统/
├── main.py                    # 主程序入口 - 图形用户界面
├── data_downloader/           # 数据下载模块
│   └── (数据获取相关代码)      # 所有下载数据的代码都在这里
├── strategies/                # 投资策略模块  
│   └── (策略文件)             # 每个文件对应一个策略
├── src/                       # 核心功能模块
│   ├── database.py            # 数据库接口
│   ├── sqlite_database.py     # SQLite数据库实现(价格数据)
│   ├── mongodb_database.py    # MongoDB数据库实现(财务数据)
│   └── visualizer.py          # 可视化分析
├── data/                      # 数据存储目录
│   ├── stock_data.db          # SQLite数据库文件(价格数据)
│   └── mongodb_data/          # MongoDB数据存储目录
├── results/                   # 结果输出目录
│   └── (策略生成的文件)        # 所有策略生成的文件都保存在这里
└── requirements.txt           # 依赖包
```

## 💡 程序设计

### 主程序流程

1. **启动程序**: 运行 `main.py` 进入图形用户界面
2. **主界面选择**: 
   - 更新数据库
   - 策略回测
3. **数据更新**: 选择要更新的具体数据库类型
4. **策略回测**: 选择要执行的具体回测策略
5. **结果输出**: 策略回测结果保存到 `results/` 文件夹

## 📊 股票数据设计

### 混合存储架构

采用 **MongoDB + SQLite 混合架构**，根据数据特性选择最适合的存储方式：

- **SQLite存储**: 结构化价格数据，支持高性能回测查询
- **MongoDB存储**: 灵活的财务报表数据，适应行业间结构差异

### 数据存储分类

#### 📈 SQLite 存储 (结构化数据)

存储在 `data/stock_data.db` 中，包含：

##### 1. 股票清单表 (stock_list)

**数据源**: `ak.stock_info_a_code_name()`

**描述**: 沪深京三个交易所的 A 股股票代码和简称

```sql
CREATE TABLE stock_list (
    stock_code TEXT PRIMARY KEY,        -- 股票代码
    stock_name TEXT NOT NULL,           -- 股票简称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段映射**:

- `stock_code` ← AKShare `code`
- `stock_name` ← AKShare `name`

##### 2. 股票基本信息表 (stock_basic_info)

**数据源**: `ak.stock_individual_info_em(symbol)`

**描述**: 个股详细信息，包括市值、行业、上市时间等

**注意**: 此API返回的是key-value格式的DataFrame，需要进行数据转换

```sql
CREATE TABLE stock_basic_info (
    stock_code TEXT PRIMARY KEY,        -- 股票代码
    stock_name TEXT,                    -- 股票简称
    total_share REAL,                   -- 总股本
    float_share REAL,                   -- 流通股
    total_market_value REAL,            -- 总市值
    float_market_value REAL,            -- 流通市值
    industry TEXT,                      -- 所属行业
    list_date TEXT,                     -- 上市时间
    latest_price REAL,                  -- 最新价格
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段映射** (从API返回的key-value格式中提取):

- `stock_code` ← 传入的symbol参数
- `latest_price` ← item='最新' 对应的 value
- `stock_name` ← item='股票简称' 对应的 value
- `total_share` ← item='总股本' 对应的 value
- `float_share` ← item='流通股' 对应的 value
- `total_market_value` ← item='总市值' 对应的 value
- `float_market_value` ← item='流通市值' 对应的 value
- `industry` ← item='行业' 对应的 value
- `list_date` ← item='上市时间' 对应的 value

##### 3. 日K线数据表 (stock_daily_kline)

**数据源**: `ak.stock_zh_a_hist(symbol, period="daily", adjust="qfq")`

**描述**: 股票日频率历史行情数据（前复权）

```sql
CREATE TABLE stock_daily_kline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,           -- 股票代码
    trade_date DATE NOT NULL,           -- 交易日期
    open_price REAL NOT NULL,           -- 开盘价
    close_price REAL NOT NULL,          -- 收盘价
    high_price REAL NOT NULL,           -- 最高价
    low_price REAL NOT NULL,            -- 最低价
    volume INTEGER,                     -- 成交量(手)
    amount REAL,                        -- 成交额(元)
    amplitude REAL,                     -- 振幅(%)
    change_pct REAL,                    -- 涨跌幅(%)
    change_amount REAL,                 -- 涨跌额(元)
    turnover_rate REAL,                 -- 换手率(%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);
```

**字段映射**:

- `trade_date` ← AKShare `日期`
- `stock_code` ← AKShare `股票代码`
- `open_price` ← AKShare `开盘`
- `close_price` ← AKShare `收盘`
- `high_price` ← AKShare `最高`
- `low_price` ← AKShare `最低`
- `volume` ← AKShare `成交量` (类型: int64)
- `amount` ← AKShare `成交额` (类型: float64)
- `amplitude` ← AKShare `振幅` (类型: float64)
- `change_pct` ← AKShare `涨跌幅` (类型: float64)
- `change_amount` ← AKShare `涨跌额` (类型: float64)
- `turnover_rate` ← AKShare `换手率` (类型: float64)

#### 🗄️ MongoDB 存储 (灵活数据)

存储在 MongoDB 数据库中，适应不同行业的字段结构差异：

##### 1. 资产负债表 (balance_sheet 集合)

**数据源**: `ak.stock_financial_report_sina(stock, symbol="资产负债表")`

**描述**: 企业资产负债表数据

**存储特点**:

- 不同行业字段结构差异巨大（银行业150列，证券业111列）
- MongoDB文档结构完美适配字段变化
- 保留所有原始字段，无数据丢失

**MongoDB 文档结构示例**:

```javascript
// 银行业资产负债表文档
{
  "_id": "000001_20250630_balance_sheet",
  "stock_code": "000001",
  "stock_name": "平安银行",
  "industry": "银行业",
  "report_date": "2025-06-30",
  "report_type": "资产负债表",
  "currency": "CNY",
  "audit_status": "未审计",
  "update_time": "2025-08-22T19:20:04",
  
  // 银行业特有字段
  "bank_assets": {
    "cash_with_central_bank": 264474000000.0,      // 现金及存放央行款项
    "deposits_from_banks": 138511000000.0,         // 存放同业款项
    "loans_to_customers": 3332319000000.0,         // 发放贷款及垫款净额
    "trading_securities": 714895000000.0           // 交易性金融资产
  },
  
  "bank_liabilities": {
    "customer_deposits": 3751641000000.0,          // 客户存款
    "central_bank_borrowing": 214228000000.0,      // 向央行借款
    "interbank_deposits": 598201000000.0           // 同业存入及拆入
  },
  
  // 通用财务字段
  "common_fields": {
    "total_assets": 5874961000000.0,               // 资产总计
    "total_liabilities": 5364899000000.0,          // 负债合计
    "shareholders_equity": 510062000000.0,         // 股东权益合计
    "retained_earnings": 259207000000.0            // 未分配利润
  },
  
  // 原始数据(保留所有150个原始字段)
  "raw_data": {
    "报告日": "20250630",
    "资产": null,
    "现金及存放中央银行款项": "264474000000.0",
    // ... 其他147个字段
  },
  
  "created_at": new Date("2025-09-03T21:15:00Z")
}

// 制造业资产负债表文档
{
  "_id": "000858_20250630_balance_sheet", 
  "stock_code": "000858",
  "stock_name": "五粮液",
  "industry": "食品饮料",
  "report_date": "2025-06-30",
  
  // 制造业特有字段
  "manufacturing_assets": {
    "inventory": 15000000000.0,                    // 存货
    "accounts_receivable": 2000000000.0,           // 应收账款
    "fixed_assets": 8000000000.0,                  // 固定资产
    "intangible_assets": 1000000000.0              // 无形资产
  },
  
  "manufacturing_liabilities": {
    "accounts_payable": 3000000000.0,              // 应付账款
    "short_term_debt": 1000000000.0                // 短期借款
  },
  
  // 通用财务字段
  "common_fields": {
    "total_assets": 50000000000.0,
    "total_liabilities": 30000000000.0,
    "shareholders_equity": 20000000000.0
  },
  
  // 原始数据(保留所有147个原始字段)
  "raw_data": { /* ... */ }
}
```

##### 2. 利润表 (income_statement 集合)

**数据源**: `ak.stock_financial_report_sina(stock, symbol="利润表")`

**描述**: 企业利润表数据

**存储特点**:

- 不同行业字段差异显著（银行业94列，证券业73列）
- 银行业有41个独有字段，制造业有30个独有字段
- 保留完整原始数据，支持行业特定分析

**MongoDB 文档结构示例**:

```javascript
// 银行业利润表文档
{
  "_id": "000001_20250630_income_statement",
  "stock_code": "000001",
  "stock_name": "平安银行",
  "industry": "银行业", 
  "report_date": "2025-06-30",
  "report_type": "利润表",
  
  // 银行业特有收入项目
  "bank_revenue": {
    "operating_revenue": 69385000000.0,        // 营业收入
    "net_interest_income": 44507000000.0,      // 净利息收入  
    "interest_income": 87931000000.0,          // 利息收入
    "interest_expense": 43424000000.0,         // 利息支出
    "fee_commission_income": 14359000000.0,    // 手续费收入
    "trading_income": 767000000.0              // 净交易收入
  },
  
  // 银行业特有支出项目  
  "bank_expenses": {
    "business_management_fee": 35000000000.0,   // 业务及管理费用
    "credit_impairment_loss": 12000000000.0     // 信用减值损失
  },
  
  // 通用利润指标
  "common_fields": {
    "net_profit": 22500000000.0,               // 净利润
    "net_profit_parent": 22400000000.0,        // 归母净利润
    "basic_eps": 1.15,                         // 基本每股收益
    "operating_profit": 32000000000.0          // 营业利润
  },
  
  // 原始数据(保留所有94个原始字段)
  "raw_data": { /* 完整原始数据 */ }
}

// 制造业利润表文档  
{
  "_id": "000858_20250630_income_statement",
  "stock_code": "000858",
  "stock_name": "五粮液",
  "industry": "食品饮料",
  
  // 制造业特有项目
  "manufacturing_revenue": {
    "operating_revenue": 52771000000.0,        // 营业收入
    "operating_cost": 12228000000.0,           // 营业成本
    "sales_expenses": 5396000000.0,            // 销售费用
    "admin_expenses": 1712000000.0,            // 管理费用
    "rd_expenses": 210000000.0                 // 研发费用
  },
  
  "common_fields": {
    "net_profit": 25000000000.0,
    "basic_eps": 6.50
  },
  
  "raw_data": { /* 完整原始数据 */ }
}
```

##### 3. 现金流量表 (cash_flow_statement 集合)

**数据源**: `ak.stock_financial_report_sina(stock, symbol="现金流量表")`

**描述**: 企业现金流量表数据

**存储特点**:

- 结构差异最大（银行业114列，制造业71列，差异43列）
- 银行业独有69个字段，制造业独有26个字段
- 行业现金流特征差异巨大，MongoDB完美适配

**MongoDB 文档结构示例**:

```javascript
// 银行业现金流量表文档
{
  "_id": "000001_20250630_cash_flow_statement",
  "stock_code": "000001", 
  "stock_name": "平安银行",
  "industry": "银行业",
  "report_date": "2025-06-30",
  "report_type": "现金流量表",
  
  // 银行业特有现金流项目
  "bank_operating_cash_flow": {
    "central_bank_borrowing_increase": 12835100000.0,     // 向央行借款净增加额
    "customer_deposits_increase": 25746400000.0,          // 客户存款净增加额  
    "loan_net_increase": 7418600000.0,                    // 客户贷款净增加额
    "interbank_funds_recovered": 2490900000.0,            // 收回拆出资金净额
    "fee_commission_cash": 96360000000.0                  // 收取手续费现金
  },
  
  "bank_investing_cash_flow": {
    "securities_investment_cash": 15000000000.0,          // 证券投资支出
    "disposal_investment_cash": 8000000000.0              // 处置投资收到现金
  },
  
  // 通用现金流量指标
  "common_fields": {
    "operating_cash_flow_net": 31137000000.0,             // 经营活动净现金流
    "investing_cash_flow_net": -5000000000.0,             // 投资活动净现金流  
    "financing_cash_flow_net": -8000000000.0,             // 筹资活动净现金流
    "cash_increase_net": 18000000000.0                    // 现金净增加额
  },
  
  // 原始数据(保留所有114个原始字段)
  "raw_data": { /* 完整原始数据 */ }
}

// 制造业现金流量表文档
{
  "_id": "000858_20250630_cash_flow_statement",
  "stock_code": "000858",
  "stock_name": "五粮液", 
  "industry": "食品饮料",
  
  // 制造业特有现金流项目
  "manufacturing_operating_cash_flow": {
    "goods_sales_cash": 69467000000.0,                    // 销售商品收到现金
    "goods_purchase_cash": 7422000000.0,                  // 购买商品支付现金
    "employee_payment_cash": 4945000000.0,                // 支付职工现金
    "tax_payment_cash": 23191000000.0                     // 支付税费现金
  },
  
  "common_fields": {
    "operating_cash_flow_net": 31137000000.0,             // 经营活动净现金流
    "investing_cash_flow_net": -2000000000.0,             // 投资活动净现金流
    "financing_cash_flow_net": -5000000000.0              // 筹资活动净现金流
  },
  
  "raw_data": { /* 完整原始数据 */ }
}
```

### 索引设计

#### SQLite 索引 (价格数据)

```sql
-- 日K线表索引
CREATE INDEX idx_stock_code_date ON stock_daily_kline(stock_code, trade_date);
CREATE INDEX idx_trade_date ON stock_daily_kline(trade_date);
CREATE INDEX idx_close_price ON stock_daily_kline(close_price);

-- 基本信息表索引
CREATE INDEX idx_industry ON stock_basic_info(industry);
CREATE INDEX idx_market_value ON stock_basic_info(total_market_value);
```

#### MongoDB 索引 (财务数据)

```javascript
// 资产负债表集合索引
db.balance_sheet.createIndex({"stock_code": 1, "report_date": -1});
db.balance_sheet.createIndex({"industry": 1, "report_date": -1});
db.balance_sheet.createIndex({"report_date": -1});
db.balance_sheet.createIndex({"common_fields.total_assets": -1});

// 利润表集合索引  
db.income_statement.createIndex({"stock_code": 1, "report_date": -1});
db.income_statement.createIndex({"industry": 1, "report_date": -1});
db.income_statement.createIndex({"common_fields.net_profit": -1});

// 现金流量表集合索引
db.cash_flow_statement.createIndex({"stock_code": 1, "report_date": -1});
db.cash_flow_statement.createIndex({"industry": 1, "report_date": -1});
db.cash_flow_statement.createIndex({"common_fields.operating_cash_flow_net": -1});

// 复合索引用于跨行业分析
db.balance_sheet.createIndex({"industry": 1, "report_date": -1, "common_fields.total_assets": -1});
```

## 🚀 快速开始

### 安装依赖

#### Python 包依赖

```bash
pip install -r requirements.txt
```

**新增依赖包**:

- `pymongo`: MongoDB Python驱动
- `motor`: MongoDB异步驱动(可选)

#### MongoDB 安装

```bash
# macOS
brew install mongodb-community

# Ubuntu/Debian  
sudo apt-get install mongodb

# 或使用Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 运行系统

```bash
python main.py
```

## 🎯 投资策略（待定)

### 🛠️ 技术实现

- **数据源**: AKShare - 提供可靠的A股历史数据
- **存储架构**:
  - **MongoDB** - 存储财务报表数据，灵活适应行业差异
  - **SQLite** - 存储价格数据，高性能回测查询
- **数据处理**: pandas + numpy - 高效的数据分析
- **可视化**: matplotlib + seaborn - 专业图表生成

## 📋 开发环境

- Python 3.8+
- pandas >= 2.0.0
- numpy >= 1.24.0
- akshare >= 1.12.0
- matplotlib >= 3.7.0
- **pymongo >= 4.0.0**

## ⚠️ 免责声明

本系统仅用于学习和研究目的，所有回测结果不构成投资建议。投资有风险，决策需谨慎。

---

*用代码验证投资策略，用数据追求真相！*
