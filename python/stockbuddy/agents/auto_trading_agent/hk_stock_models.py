"""Data models for HK Stock Trading Agent

Models for Hong Kong stock trading configuration and requests.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# Constants
DEFAULT_INITIAL_CAPITAL_HKD = 1000000.0  # 1 million HKD
DEFAULT_MAX_POSITIONS = 5
DEFAULT_RISK_PER_TRADE = 0.05  # 5% of capital per trade
MAX_SYMBOLS = 10
DEFAULT_CHECK_INTERVAL = 300  # 5 minutes (HK market updates)

SUPPORTED_EXCHANGES = {"hk_stock_paper", "hk_stock_live"}


class HKStockTradingRequest(BaseModel):
    """HK Stock trading request model for parsing natural language queries"""

    stock_symbols: List[str] = Field(
        ...,
        description="List of HK stock symbols to trade (e.g., ['00700', '09988', '00941'])",
    )
    initial_capital: Optional[float] = Field(
        default=DEFAULT_INITIAL_CAPITAL_HKD,
        description="Initial capital for trading in HKD",
        gt=0,
    )
    exchange: Optional[str] = Field(
        default="hk_stock_paper",
        description="Exchange adapter to use (hk_stock_paper or hk_stock_live)",
    )
    check_interval: Optional[int] = Field(
        default=DEFAULT_CHECK_INTERVAL,
        description="Check interval in seconds (default: 5 minutes)",
        gt=0,
    )
    risk_per_trade: Optional[float] = Field(
        default=DEFAULT_RISK_PER_TRADE,
        description="Risk per trade as percentage of capital",
        gt=0,
        lt=1,
    )
    max_positions: Optional[int] = Field(
        default=DEFAULT_MAX_POSITIONS,
        description="Maximum number of concurrent positions",
        gt=0,
    )
    broker: Optional[str] = Field(
        default=None,
        description="Broker for live trading (futu, ib, tiger, hithink)",
    )

    @field_validator("stock_symbols")
    @classmethod
    def validate_symbols(cls, v):
        """Validate and normalize stock symbols."""
        if not v or len(v) == 0:
            raise ValueError("At least one stock symbol is required")
        if len(v) > MAX_SYMBOLS:
            raise ValueError(f"Maximum {MAX_SYMBOLS} symbols allowed")
        
        # Normalize symbols (remove HKEX: prefix if present, pad to 5 digits)
        normalized = []
        for symbol in v:
            clean_symbol = symbol.upper().replace("HKEX:", "")
            # Pad to 5 digits
            padded = clean_symbol.zfill(5)
            normalized.append(padded)
        
        return normalized

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value):
        """Validate exchange type."""
        if value is None:
            return "hk_stock_paper"  # Default to paper trading
        
        lowered = value.lower()
        if lowered not in SUPPORTED_EXCHANGES:
            raise ValueError(
                f"Unsupported exchange '{value}'. "
                f"Supported: {', '.join(SUPPORTED_EXCHANGES)}"
            )
        return lowered


class HKStockConfig(BaseModel):
    """Configuration for HK stock trading agent"""

    initial_capital: float = Field(
        default=DEFAULT_INITIAL_CAPITAL_HKD,
        description="Initial capital for trading in HKD",
        gt=0,
    )
    stock_symbols: List[str] = Field(
        ...,
        description="List of HK stock symbols to trade (5-digit codes)",
        max_length=MAX_SYMBOLS,
    )
    check_interval: int = Field(
        default=DEFAULT_CHECK_INTERVAL,
        description="Check interval in seconds",
        gt=0,
    )
    risk_per_trade: float = Field(
        default=DEFAULT_RISK_PER_TRADE,
        description="Risk per trade as percentage of capital",
        gt=0,
        lt=1,
    )
    max_positions: int = Field(
        default=DEFAULT_MAX_POSITIONS,
        description="Maximum number of concurrent positions",
        gt=0,
    )
    exchange: str = Field(
        default="hk_stock_paper",
        description="Exchange adapter to use",
    )
    broker: Optional[str] = Field(
        default=None,
        description="Broker for live trading (futu, ib, tiger, hithink)",
    )
    # Broker API credentials (for live trading)
    broker_api_key: Optional[str] = Field(
        default=None,
        description="Broker API key",
        repr=False,
    )
    broker_api_secret: Optional[str] = Field(
        default=None,
        description="Broker API secret",
        repr=False,
    )
    broker_account_id: Optional[str] = Field(
        default=None,
        description="Broker account ID",
        repr=False,
    )
    # AI model configuration
    use_ai_signals: bool = Field(
        default=False,
        description="Whether to use AI model for enhanced signal generation",
    )
    agent_model: Optional[str] = Field(
        default=None,
        description="Model ID for AI-enhanced trading decisions",
    )
    agent_provider: Optional[str] = Field(
        default=None,
        description="Provider name (null = auto-detect from config system)",
    )

    @field_validator("stock_symbols")
    @classmethod
    def validate_symbols(cls, v):
        """Validate stock symbols."""
        if not v or len(v) == 0:
            raise ValueError("At least one stock symbol is required")
        if len(v) > MAX_SYMBOLS:
            raise ValueError(f"Maximum {MAX_SYMBOLS} symbols allowed")
        
        # Ensure all symbols are 5-digit codes
        for symbol in v:
            if not symbol.isdigit() or len(symbol) != 5:
                raise ValueError(
                    f"Invalid HK stock symbol '{symbol}'. "
                    "Expected 5-digit code (e.g., '00700', '09988')"
                )
        
        return v

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value: str) -> str:
        """Validate exchange type."""
        lowered = value.lower()
        if lowered not in SUPPORTED_EXCHANGES:
            raise ValueError(
                f"Unsupported exchange '{value}'. "
                f"Supported: {', '.join(SUPPORTED_EXCHANGES)}"
            )
        return lowered


class HKStockPosition(BaseModel):
    """Represents a position in a HK stock"""

    symbol: str = Field(..., description="Stock symbol (5-digit code)")
    quantity: int = Field(..., description="Position size in shares", ge=0)
    entry_price: float = Field(..., description="Average entry price in HKD", gt=0)
    current_price: Optional[float] = Field(None, description="Current market price in HKD")
    unrealized_pnl: Optional[float] = Field(None, description="Unrealized P&L in HKD")
    unrealized_pnl_pct: Optional[float] = Field(None, description="Unrealized P&L %")
    lot_size: int = Field(default=100, description="Lot size for this stock")

    def calculate_pnl(self, current_price: float):
        """Calculate unrealized P&L."""
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        self.unrealized_pnl_pct = (
            (current_price - self.entry_price) / self.entry_price * 100
        )


class HKStockTradeSignal(BaseModel):
    """Trading signal for a HK stock"""

    symbol: str = Field(..., description="Stock symbol")
    action: str = Field(..., description="BUY, SELL, or HOLD")
    confidence: float = Field(..., description="Confidence level (0-1)", ge=0, le=1)
    reasons: List[str] = Field(default=[], description="Reasons for the signal")
    suggested_lots: Optional[int] = Field(None, description="Suggested lots to trade")
    stop_loss: Optional[float] = Field(None, description="Suggested stop loss price")
    take_profit: Optional[float] = Field(None, description="Suggested take profit price")

