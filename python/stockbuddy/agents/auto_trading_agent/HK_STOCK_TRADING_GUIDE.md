# Hong Kong Stock Auto-Trading Guide 🇭🇰📈

本指南介绍如何使用StockBuddy v3的香港股票自动交易功能。

## 目录
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [模拟交易示例](#模拟交易示例)
- [进阶配置](#进阶配置)
- [真实交易（后续）](#真实交易)

---

## 功能特性

### ✅ 已实现（Phase 1）- 模拟交易系统

1. **HK股票模拟交易**
   - 完整的港股交易模拟（Paper Trading）
   - 真实的市场费用计算（印花税、交易征费等）
   - 支持最小交易单位（lot size）
   - HKD港币计价

2. **市场数据集成**
   - 实时价格（via AKShareAdapter / YFinanceAdapter）
   - 历史K线数据
   - 技术指标（MA, RSI, MACD, Bollinger Bands）

3. **港股特有功能**
   - AH股溢价监控
   - 港股通资金流向分析
   - 恒生指数相关性
   - 交易时间检查（09:30-12:00, 13:00-16:00 HKT）

4. **风险管理**
   - 仓位管理
   - 止损/止盈
   - 最大持仓限制
   - 单笔交易风险控制

### 🔜 计划中（Phase 2）- 真实交易API集成

- 富途证券（Futu）API
- 盈透证券（Interactive Brokers）API
- 老虎证券（Tiger Trade）API
- 华盛证券（Hithink）API

---

## 系统架构

```
┌─────────────────────────────────────────┐
│     HK Stock Trading Agent              │
│                                         │
│  - Strategy Analysis                    │
│  - Portfolio Management                 │
│  - Risk Control                         │
└────────────┬────────────────────────────┘
             │
        ┌────┴────┐
        │         │
┌───────▼──┐  ┌──▼─────────────────────┐
│ Market   │  │ Exchange Adapter       │
│ Data     │  │                        │
│ Provider │  │ - HKStockPaperTrading  │
│          │  │ - [Future: Futu/IB]    │
└────┬─────┘  └────────────────────────┘
     │
     │ ┌─────────────────────┐
     ├─► AdapterManager      │
     │ │ - AKShareAdapter    │
     │ │ - YFinanceAdapter   │
     │ └─────────────────────┘
     │
     │ ┌─────────────────────┐
     ├─► AHPremiumAdapter    │
     │ │ (AH股溢价)          │
     │ └─────────────────────┘
     │
     │ ┌─────────────────────┐
     └─► HKConnectAdapter    │
       │ (港股通资金流向)     │
       └─────────────────────┘
```

---

## 快速开始

### 1. 安装依赖

确保已安装所有依赖：

```bash
cd python
uv sync
```

### 2. 配置环境变量（可选）

创建或编辑 `.env` 文件：

```bash
# HK Stock Trading Configuration
HK_STOCK_INITIAL_CAPITAL=1000000  # 初始资金（HKD）
HK_STOCK_MAX_POSITIONS=5          # 最大持仓数
HK_STOCK_RISK_PER_TRADE=0.05      # 单笔风险（5%）
HK_STOCK_CHECK_INTERVAL=300       # 检查间隔（秒）
```

### 3. 基本使用示例

#### Python脚本方式

```python
from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading
from stockbuddy.agents.auto_trading_agent.hk_stock_market_data import (
    get_hk_stock_market_data_provider
)
from stockbuddy.agents.auto_trading_agent.hk_stock_models import HKStockConfig

# 创建配置
config = HKStockConfig(
    initial_capital=1000000.0,  # 100万HKD
    stock_symbols=["00700", "09988", "00941"],  # 腾讯、阿里、中移动
    check_interval=300,  # 5分钟
    risk_per_trade=0.05,  # 5%
    max_positions=3,
    exchange="hk_stock_paper",
)

# 初始化交易所
exchange = HKStockPaperTrading(initial_capital=config.initial_capital)

# 初始化市场数据提供商
market_data = get_hk_stock_market_data_provider()

# 获取实时价格
async def get_price_example():
    price = await exchange.get_current_price("HKEX:00700")
    print(f"腾讯当前价格: ${price:.2f} HKD")

# 获取交易信号
signal = market_data.generate_trading_signal("HKEX:00700", days=60)
print(f"交易信号: {signal['signal']}, 置信度: {signal['confidence']:.2f}")
print(f"原因: {', '.join(signal['reasons'])}")

# 执行买入（如果信号为BUY）
async def execute_buy_example():
    if signal['signal'] == "BUY":
        order = await exchange.execute_buy(
            symbol="HKEX:00700",
            quantity=1,  # 1手（100股）
            price=None,  # 市价
        )
        if order:
            print(f"订单成功: {order.order_id}")
```

---

## 模拟交易示例

### 示例1：单股票交易

```python
import asyncio
from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading
from stockbuddy.agents.auto_trading_agent.hk_stock_market_data import (
    get_hk_stock_market_data_provider
)

async def single_stock_trading():
    """单股票交易示例"""
    
    # 初始化
    exchange = HKStockPaperTrading(initial_balance=500000.0)  # 50万HKD
    market_data = get_hk_stock_market_data_provider()
    
    symbol = "HKEX:00700"  # 腾讯控股
    
    # 1. 获取当前价格
    current_price = await exchange.get_current_price(symbol)
    print(f"腾讯当前价格: ${current_price:.2f} HKD")
    
    # 2. 获取交易信号
    signal = market_data.generate_trading_signal(symbol, days=60)
    print(f"\n交易信号:")
    print(f"  动作: {signal['signal']}")
    print(f"  置信度: {signal['confidence']:.2f}")
    print(f"  原因: {', '.join(signal['reasons'])}")
    
    # 3. 如果信号为BUY，执行买入
    if signal['signal'] == "BUY":
        lots_to_buy = 2  # 买入2手（200股）
        order = await exchange.execute_buy(symbol, quantity=lots_to_buy)
        
        if order:
            print(f"\n买入成功:")
            print(f"  订单ID: {order.order_id}")
            print(f"  数量: {order.quantity}股 ({lots_to_buy}手)")
            print(f"  价格: ${order.price:.2f} HKD")
            print(f"  总金额: ${order.quantity * order.price:.2f} HKD")
    
    # 4. 查看账户余额
    balance = await exchange.get_balance()
    print(f"\n当前账户:")
    print(f"  现金: ${balance['HKD']:,.2f} HKD")
    
    # 5. 查看持仓
    positions = await exchange.get_open_positions()
    for sym, pos in positions.items():
        print(f"\n持仓 - {sym}:")
        print(f"  数量: {pos['quantity']}股")
        print(f"  成本: ${pos['entry_price']:.2f} HKD")

# 运行
asyncio.run(single_stock_trading())
```

### 示例2：多股票组合交易

```python
import asyncio
from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading
from stockbuddy.agents.auto_trading_agent.hk_stock_market_data import (
    get_hk_stock_market_data_provider
)

async def portfolio_trading():
    """多股票组合交易示例"""
    
    # 初始化
    exchange = HKStockPaperTrading(initial_balance=2000000.0)  # 200万HKD
    market_data = get_hk_stock_market_data_provider()
    
    # 股票池
    stock_list = [
        "HKEX:00700",  # 腾讯控股
        "HKEX:09988",  # 阿里巴巴
        "HKEX:00941",  # 中国移动
        "HKEX:03690",  # 美团
        "HKEX:01810",  # 小米集团
    ]
    
    print("=== 港股组合交易分析 ===\n")
    
    # 分析所有股票
    signals = []
    for symbol in stock_list:
        signal = market_data.generate_trading_signal(symbol, days=60)
        signals.append(signal)
        
        print(f"{symbol}:")
        print(f"  信号: {signal['signal']}")
        print(f"  置信度: {signal['confidence']:.2f}")
        print(f"  原因: {', '.join(signal['reasons'][:2])}")
        print()
    
    # 筛选BUY信号并排序
    buy_signals = [s for s in signals if s['signal'] == "BUY"]
    buy_signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"\n发现 {len(buy_signals)} 个买入信号")
    
    # 执行前3个最强的BUY信号
    max_positions = 3
    for i, signal in enumerate(buy_signals[:max_positions]):
        symbol = signal['symbol']
        print(f"\n执行买入 #{i+1}: {symbol}")
        
        # 每个仓位分配20%资金
        available_cash = (await exchange.get_balance())['HKD']
        allocation = available_cash * 0.2
        
        # 获取当前价格
        current_price = await exchange.get_current_price(symbol)
        
        # 计算可以买几手
        lot_size = exchange.get_lot_size(symbol)
        max_shares = int(allocation / current_price)
        lots = max(1, max_shares // lot_size)
        
        # 执行买入
        order = await exchange.execute_buy(symbol, quantity=lots)
        
        if order:
            print(f"  成功: {lots}手 ({order.quantity}股) @ ${order.price:.2f}")
        else:
            print(f"  失败: 资金不足或其他原因")
    
    # 最终持仓报告
    print("\n=== 持仓报告 ===")
    positions = await exchange.get_open_positions()
    
    total_position_value = 0
    for symbol, pos in positions.items():
        current_price = await exchange.get_current_price(symbol)
        market_value = pos['quantity'] * current_price
        pnl = (current_price - pos['entry_price']) * pos['quantity']
        pnl_pct = (pnl / (pos['quantity'] * pos['entry_price'])) * 100
        
        total_position_value += market_value
        
        print(f"\n{symbol}:")
        print(f"  数量: {pos['quantity']}股")
        print(f"  成本: ${pos['entry_price']:.2f}")
        print(f"  现价: ${current_price:.2f}")
        print(f"  市值: ${market_value:,.2f}")
        print(f"  盈亏: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
    
    balance = await exchange.get_balance()
    total_assets = balance['HKD'] + total_position_value
    
    print(f"\n总资产: ${total_assets:,.2f} HKD")
    print(f"现金: ${balance['HKD']:,.2f} HKD")
    print(f"持仓市值: ${total_position_value:,.2f} HKD")

# 运行
asyncio.run(portfolio_trading())
```

---

## 进阶配置

### 1. 自定义Lot Size

如果需要为某个股票自定义lot size，编辑：

```python
# python/stockbuddy/agents/auto_trading_agent/exchanges/hk_stock_paper_trading.py

HK_STOCK_LOT_SIZES = {
    "00700": 100,  # 腾讯控股
    "09988": 50,   # 阿里巴巴-SW
    # 添加更多...
}
```

### 2. 调整费用结构

如果需要修改交易费用，编辑HKStockPaperTrading的__init__方法：

```python
self.stamp_duty_rate = 0.0013      # 印花税 0.13%
self.trading_fee_rate = 0.00005    # 交易费 0.005%
self.settlement_fee_rate = 0.00002 # 结算费 0.002%
self.transaction_levy_rate = 0.000027  # 交易征费 0.0027%
```

### 3. AI增强信号（可选）

使用AI模型增强交易信号生成：

```python
config = HKStockConfig(
    # ... 其他配置
    use_ai_signals=True,
    agent_model="gpt-4",
    agent_provider="openai",
)
```

---

## 真实交易

### ⚠️ 警告

真实交易涉及真金白银，存在巨大风险。在使用真实交易前：

1. **充分测试**：在Paper Trading环境下至少测试1个月
2. **小额开始**：初始资金不超过你可承受损失的金额
3. **理解风险**：股市有风险，投资需谨慎
4. **合规性**：确保你的交易符合当地法律法规

### Phase 2计划：券商API集成

我们计划支持以下券商：

1. **富途证券（Futu）**
   - 最流行的港股交易API
   - 文档：https://openapi.futunn.com/
   - 优点：中文文档完善，手续费低

2. **盈透证券（Interactive Brokers）**
   - 全球性券商
   - 文档：https://interactivebrokers.github.io/
   - 优点：支持全球市场，专业级工具

3. **老虎证券（Tiger Trade）**
   - 国内投资者友好
   - 优点：支持A股+港股+美股

4. **华盛证券（Hithink）**
   - 香港本地券商
   - 优点：港股交易成本低

### 使用真实交易（示例，待实现）

```python
# 未来的使用方式（示例）
from stockbuddy.agents.auto_trading_agent.exchanges import FutuExchange

exchange = FutuExchange(
    api_key="your_api_key",
    api_secret="your_api_secret",
    account_id="your_account_id",
    environment="paper",  # 先用Futu的Paper Trading测试
)

# 其余代码与Paper Trading相同
```

---

## 常见问题

### Q1: 模拟交易的价格数据准确吗？
**A:** 价格数据来自AKShareAdapter和YFinanceAdapter，是真实的市场数据，有轻微延迟（通常1-5分钟）。对于模拟交易来说足够准确。

### Q2: 可以同时交易A股和港股吗？
**A:** 当前版本的HK Stock Trading Agent专注于港股。A股交易可以使用原有的系统（或后续扩展）。

### Q3: Lot size是什么？
**A:** Lot size（每手股数）是香港股市的最小交易单位。大部分股票是100股/手，但有些是50股/手、200股/手等。系统会自动处理。

### Q4: 如何处理交易时间？
**A:** 系统会检查香港股市的交易时间（09:30-16:00）和竞价时段。在Paper Trading模式下，可以在任何时间交易（模拟），但生产环境会严格遵守交易时间。

### Q5: 支持做空吗？
**A:** 当前版本不支持做空。未来可以通过券商API支持融券做空。

---

## 文件结构

```
python/stockbuddy/agents/auto_trading_agent/
├── exchanges/
│   ├── base_exchange.py           # 交易所基类
│   ├── hk_stock_paper_trading.py  # 港股模拟交易 ⭐
│   ├── okx_exchange.py             # OKX（加密货币）
│   └── paper_trading.py            # 加密货币模拟交易
├── hk_stock_models.py             # 港股交易models ⭐
├── hk_stock_market_data.py        # 港股市场数据提供商 ⭐
├── HK_STOCK_TRADING_GUIDE.md      # 本文档 ⭐
└── agent.py                        # AutoTradingAgent (加密货币)
```

⭐ = HK Stock Trading新增文件

---

## 下一步计划

- [ ] 创建HKStockTradingAgent（完整的agent实现）
- [ ] 集成到Super Agent路由
- [ ] 前端UI支持（显示港股持仓、交易记录）
- [ ] 富途证券API集成
- [ ] 回测系统（backtesting）
- [ ] AI增强决策（深度学习模型）

---

## 贡献

欢迎贡献代码、报告bug或提出建议！

---

## 免责声明

**本软件仅供学习和研究使用。使用本软件进行实际交易的任何损失，开发者不承担任何责任。投资有风险，入市需谨慎。**

---

*最后更新: 2025-11-18*

