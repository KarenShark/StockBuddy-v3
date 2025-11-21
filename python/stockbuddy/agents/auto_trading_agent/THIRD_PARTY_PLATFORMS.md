# 第三方港股模拟交易平台API对接方案

## 概述

本文档提供港股模拟交易平台的API对接建议，帮助你从内部模拟盘过渡到真实市场数据和模拟交易环境。

---

## 🌟 推荐平台

### 1. 富途证券 (Futu) OpenAPI ⭐️⭐️⭐️⭐️⭐️

**优势**：
- ✅ 港股、美股、A股全覆盖
- ✅ 提供官方Python SDK (`futu-api`)
- ✅ 支持实盘和模拟盘（Paper Trading）
- ✅ 实时行情数据（Level-1免费）
- ✅ 完善的技术指标和历史数据
- ✅ 中文文档完善

**免费额度**：
- 实时行情：前3个月免费，之后约$5/月
- 模拟盘：完全免费
- API调用：无限制

**快速开始**：
```bash
pip install futu-api
```

**示例代码**：
```python
from futu import OpenQuoteContext, RET_OK

# 连接富途OpenD
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 获取股票报价
ret, data = quote_ctx.get_market_snapshot(['HK.00700'])
if ret == RET_OK:
    print(data)

quote_ctx.close()
```

**官网**: https://openapi.futunn.com/

---

### 2. 老虎证券 (Tiger) OpenAPI ⭐️⭐️⭐️⭐️

**优势**：
- ✅ 支持港股、美股、A股
- ✅ 提供Python SDK (`tigeropen`)
- ✅ 模拟账户免费
- ✅ RESTful API + WebSocket
- ✅ 支持期权和期货

**免费额度**：
- 模拟账户：完全免费
- 实时行情：需要订阅（约$10/月）
- API调用：每秒120次

**快速开始**：
```bash
pip install tigeropen
```

**示例代码**：
```python
from tigeropen.common.consts import Language, Market
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig

# 配置
config = TigerOpenClientConfig(sandbox_debug=True)
config.language = Language.zh_CN

# 创建Quote客户端
quote_client = QuoteClient(config)

# 获取报价
data = quote_client.get_market_brief(symbols=['00700'])
print(data)
```

**官网**: https://quant.itigerup.com/

---

### 3. 盈透证券 (Interactive Brokers) API ⭐️⭐️⭐️⭐

**优势**：
- ✅ 全球市场覆盖
- ✅ 专业级交易平台
- ✅ 模拟账户（Paper Trading）
- ✅ Python库 (`ib_insync`)
- ✅ 低手续费

**劣势**：
- ❌ 开户门槛较高（$10,000）
- ❌ 接口复杂度较高
- ❌ 中文文档较少

**快速开始**：
```bash
pip install ib_insync
```

**示例代码**：
```python
from ib_insync import IB, Stock

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)  # Paper Trading

# 港股需要使用SEHK交易所
contract = Stock('700', 'SEHK', 'HKD')
ticker = ib.reqMktData(contract)

ib.sleep(2)
print(ticker.marketPrice())

ib.disconnect()
```

**官网**: https://www.interactivebrokers.com/

---

### 4. Yahoo Finance API (免费) ⭐️⭐️⭐️

**优势**：
- ✅ 完全免费
- ✅ 无需注册
- ✅ Python库 (`yfinance`)
- ✅ 历史数据和实时行情
- ✅ 简单易用

**劣势**：
- ❌ 不支持模拟交易（仅数据）
- ❌ 无官方API支持
- ❌ 数据延迟约15分钟

**快速开始**：
```bash
pip install yfinance
```

**示例代码**：
```python
import yfinance as yf

# 港股需要加.HK后缀
ticker = yf.Ticker("0700.HK")

# 获取实时数据
info = ticker.info
print(f"当前价: {info['currentPrice']}")

# 获取历史数据
hist = ticker.history(period="1mo")
print(hist)
```

---

### 5. Polygon.io ⭐️⭐️⭐️

**优势**：
- ✅ 专业金融数据API
- ✅ 实时和历史数据
- ✅ RESTful API + WebSocket
- ✅ 免费tier可用

**劣势**：
- ❌ 港股支持有限（主要是美股）
- ❌ 不支持交易（仅数据）

---

## 📊 功能对比表

| 平台 | 模拟交易 | 港股支持 | 实时行情 | 免费额度 | Python SDK | 推荐指数 |
|------|---------|---------|---------|---------|-----------|---------|
| 富途 | ✅ | ✅ | ✅ | 高 | ✅ | ⭐️⭐️⭐️⭐️⭐️ |
| 老虎 | ✅ | ✅ | ✅ | 中 | ✅ | ⭐️⭐️⭐️⭐️ |
| 盈透 | ✅ | ✅ | ✅ | 高 | ✅ | ⭐️⭐️⭐️⭐ |
| Yahoo Finance | ❌ | ✅ | ⏱️ | 无限 | ✅ | ⭐️⭐️⭐️ |
| Polygon.io | ❌ | ⚠️ | ✅ | 低 | ✅ | ⭐️⭐️⭐️ |

---

## 🛠️ 集成到StockBuddy的方案

### 方案1：创建新的Exchange Adapter

在 `python/stockbuddy/agents/auto_trading_agent/exchanges/` 下创建：

```python
# futu_exchange.py
from futu import OpenQuoteContext, OpenSecTradeContext, TrdEnv
from .base_exchange import ExchangeBase

class FutuExchange(ExchangeBase):
    """富途证券Exchange适配器"""
    
    def __init__(self, host='127.0.0.1', port=11111, env=TrdEnv.SIMULATE):
        self.host = host
        self.port = port
        self.env = env  # TrdEnv.SIMULATE 或 TrdEnv.REAL
        
        self.quote_ctx = OpenQuoteContext(host=host, port=port)
        self.trade_ctx = OpenSecTradeContext(host=host, port=port)
        
    async def get_balance(self) -> dict:
        ret, data = self.trade_ctx.accinfo_query()
        if ret == RET_OK:
            return {
                'cash': float(data['cash'][0]),
                'market_value': float(data['market_val'][0]),
                'total_assets': float(data['total_assets'][0])
            }
        return {}
    
    async def place_order(self, symbol: str, side: str, quantity: int, price: float = None):
        # 实现下单逻辑
        pass
```

### 方案2：混合模式 - 真实数据 + 模拟交易

**最佳实践**：使用第三方API获取真实市场数据，但在本地模拟交易

```python
# hk_stock_market_data.py 修改

import yfinance as yf

async def get_real_time_price(symbol: str) -> float:
    """从Yahoo Finance获取实时价格"""
    ticker = yf.Ticker(f"{symbol}.HK")
    return ticker.info.get('currentPrice', 0)

async def get_historical_data(symbol: str, period: str = "1mo"):
    """获取历史K线数据"""
    ticker = yf.Ticker(f"{symbol}.HK")
    return ticker.history(period=period)
```

---

## 🚀 快速集成步骤

### Step 1: 选择平台（推荐富途）

1. 下载富途牛牛App
2. 注册账号（免费）
3. 申请开通OpenAPI权限
4. 下载FutuOpenD客户端

### Step 2: 安装SDK

```bash
cd python
uv pip install futu-api yfinance
```

### Step 3: 创建Adapter

参考上面的 `FutuExchange` 示例代码

### Step 4: 更新配置

```yaml
# python/configs/agents/hk_stock_agent.yaml
trading:
  exchange_type: "futu_simulate"  # 新增
  futu_host: "127.0.0.1"
  futu_port: 11111
  use_real_data: true  # 使用真实市场数据
```

### Step 5: 测试连接

```python
# test_futu_connection.py
from futu import OpenQuoteContext, RET_OK

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_market_snapshot(['HK.00700'])

if ret == RET_OK:
    print("✅ 富途API连接成功！")
    print(data)
else:
    print(f"❌ 连接失败: {data}")

quote_ctx.close()
```

---

## 💡 建议

### 当前阶段建议：

1. **短期（1-2周）**：
   - 继续使用内部Paper Trading
   - 集成 `yfinance` 获取真实股价数据
   - 完善策略逻辑和UI

2. **中期（1个月）**：
   - 集成富途OpenAPI
   - 使用富途模拟盘进行测试
   - 验证交易策略效果

3. **长期（3个月+）**：
   - 策略验证成熟后，考虑实盘小资金测试
   - 逐步迁移到真实交易环境

### 为什么先用yfinance？

✅ **零成本**：无需注册，立即可用  
✅ **低门槛**：一行代码获取数据  
✅ **够用**：数据质量足够策略测试  
✅ **平滑过渡**：代码改动最小  

---

## 📝 示例：集成yfinance到现有系统

```python
# hk_stock_market_data.py 添加

import yfinance as yf

class HKStockMarketDataProvider:
    def __init__(self, use_real_data: bool = False):
        self.use_real_data = use_real_data
    
    async def get_price(self, symbol: str) -> float:
        if self.use_real_data:
            return self._get_real_price(symbol)
        else:
            return self._get_simulated_price(symbol)
    
    def _get_real_price(self, symbol: str) -> float:
        """从Yahoo Finance获取真实价格"""
        try:
            ticker = yf.Ticker(f"{symbol}.HK")
            info = ticker.info
            return info.get('currentPrice', info.get('regularMarketPrice', 0))
        except Exception as e:
            logger.warning(f"获取{symbol}价格失败: {e}")
            return 0
    
    def _get_simulated_price(self, symbol: str) -> float:
        """模拟价格（原有逻辑）"""
        base_prices = {
            "00700": 320.0,
            "09988": 75.0,
            # ...
        }
        base = base_prices.get(symbol, 100.0)
        return base * (1 + random.uniform(-0.02, 0.02))
```

---

## 🎯 总结

**我的推荐路径**：

1. ✅ **现在**：使用内部Paper Trading + yfinance真实数据
2. ⏭️ **下一步**：集成富途模拟盘（1-2周后）
3. 🚀 **未来**：策略成熟后考虑实盘

这样既能快速迭代开发，又能逐步验证策略有效性，最终平滑过渡到真实交易环境。

**需要我帮你立即集成yfinance吗？** 只需5分钟就能让你的系统使用真实市场数据！

