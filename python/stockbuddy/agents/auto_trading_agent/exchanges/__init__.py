"""Exchange adapters for different trading platforms

This module provides adapters for various exchanges:
- Cryptocurrency exchanges (OKX, Binance, paper trading)
- Hong Kong stock market (paper trading and live trading)

Adapters:
- ExchangeBase: Abstract base class defining the exchange interface
- PaperTrading: Crypto simulated trading (default)
- BinanceExchange: Live trading on Binance (requires API keys)
- OKXExchange: Live trading on OKX (requires API keys)
- HKStockPaperTrading: HK stock simulated trading
"""

from .base_exchange import ExchangeBase, ExchangeType, Order, OrderStatus
from .hk_stock_paper_trading import HKStockPaperTrading
from .okx_exchange import OKXExchange, OKXExchangeError
from .paper_trading import PaperTrading

# FutuExchange is optional - only available if futu-api is installed
try:
    from .futu_exchange import FutuExchange
    _FUTU_AVAILABLE = True
except ImportError:
    _FUTU_AVAILABLE = False
    FutuExchange = None  # type: ignore

__all__ = [
    "ExchangeBase",
    "ExchangeType",
    "Order",
    "OrderStatus",
    "OKXExchange",
    "OKXExchangeError",
    "PaperTrading",
    "HKStockPaperTrading",
]

if _FUTU_AVAILABLE:
    __all__.append("FutuExchange")
