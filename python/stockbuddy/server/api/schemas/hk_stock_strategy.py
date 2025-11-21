"""HK Stock Strategy API Schemas"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .base import SuccessResponse


# ============================================
# Request Schemas
# ============================================

class CreateHKStockStrategyRequest(BaseModel):
    """Request to create a new HK stock trading strategy"""
    strategy_name: str = Field(..., description="Strategy name")
    symbols: List[str] = Field(..., description="List of HK stock symbols (e.g., ['00700', '09988'])")
    initial_capital: float = Field(default=1000000.0, description="Initial capital in HKD")
    max_position_size: float = Field(default=0.3, description="Max position size as % of capital (0-1)")
    max_positions: int = Field(default=5, description="Maximum number of positions")
    strategy_prompt: str = Field(..., description="Strategy trading logic description")
    rebalance_interval: int = Field(default=300, description="Rebalance interval in seconds")


class UpdateHKStockStrategyRequest(BaseModel):
    """Request to update strategy parameters"""
    status: Optional[str] = Field(None, description="Strategy status: running, stopped")
    max_position_size: Optional[float] = Field(None, description="Max position size")
    max_positions: Optional[int] = Field(None, description="Max positions")


# ============================================
# Response Schemas
# ============================================

class HKStockStrategyInfo(BaseModel):
    """HK Stock Strategy basic info"""
    strategy_id: str = Field(..., description="Strategy ID")
    strategy_name: str = Field(..., description="Strategy name")
    symbols: List[str] = Field(..., description="Trading symbols")
    status: str = Field(..., description="Status: running, stopped")
    initial_capital: float = Field(..., description="Initial capital (HKD)")
    current_value: float = Field(..., description="Current portfolio value (HKD)")
    total_pnl: float = Field(..., description="Total P&L (HKD)")
    total_pnl_pct: float = Field(..., description="Total P&L percentage")
    position_count: int = Field(..., description="Number of open positions")
    trade_count: int = Field(..., description="Total number of trades")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")


class HKStockStrategyDetail(HKStockStrategyInfo):
    """Detailed HK Stock Strategy information"""
    strategy_prompt: str = Field(..., description="Strategy trading logic")
    max_position_size: float = Field(..., description="Max position size")
    max_positions: int = Field(..., description="Max positions")
    rebalance_interval: int = Field(..., description="Rebalance interval (seconds)")
    last_rebalance: Optional[datetime] = Field(None, description="Last rebalance time")


class HKStrategyPosition(BaseModel):
    """Position in HK stock strategy"""
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Position quantity (shares)")
    lots: int = Field(..., description="Number of lots")
    avg_price: float = Field(..., description="Average entry price (HKD)")
    current_price: float = Field(..., description="Current price (HKD)")
    market_value: float = Field(..., description="Market value (HKD)")
    cost_basis: float = Field(..., description="Cost basis (HKD)")
    unrealized_pnl: float = Field(..., description="Unrealized P&L (HKD)")
    unrealized_pnl_pct: float = Field(..., description="Unrealized P&L %")


class HKStrategyTrade(BaseModel):
    """Trade executed by strategy"""
    trade_id: str = Field(..., description="Trade ID")
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="Trade side: BUY, SELL")
    quantity: int = Field(..., description="Quantity (shares)")
    lots: int = Field(..., description="Number of lots")
    price: float = Field(..., description="Execution price (HKD)")
    total_value: float = Field(..., description="Total trade value (HKD)")
    fees: float = Field(..., description="Fees paid (HKD)")
    timestamp: datetime = Field(..., description="Trade timestamp")
    reason: Optional[str] = Field(None, description="Trade reason/signal")


class HKStrategyPerformancePoint(BaseModel):
    """Performance data point"""
    timestamp: datetime = Field(..., description="Timestamp")
    portfolio_value: float = Field(..., description="Total portfolio value (HKD)")
    cash: float = Field(..., description="Cash balance (HKD)")
    positions_value: float = Field(..., description="Positions value (HKD)")
    pnl: float = Field(..., description="Total P&L (HKD)")
    pnl_pct: float = Field(..., description="P&L percentage")


class HKStrategyAIRecommendation(BaseModel):
    """AI recommendation for a specific symbol"""
    symbol: str = Field(..., description="Stock symbol")
    action: str = Field(..., description="Recommended action: BUY, SELL, HOLD")
    lots: int = Field(..., description="Recommended lot size")
    reason: str = Field(..., description="Reason for the recommendation")
    confidence: float = Field(..., description="Confidence score (0-1)")
    target_price: Optional[float] = Field(None, description="Target price if any")
    executed: Optional[bool] = Field(None, description="Whether recommendation was executed")
    trade_id: Optional[str] = Field(None, description="Trade ID if executed")


class HKStrategyAIDecision(BaseModel):
    """AI decision record"""
    timestamp: datetime = Field(..., description="Decision timestamp")
    portfolio_value: float = Field(..., description="Portfolio value at decision time (HKD)")
    cash: float = Field(..., description="Cash balance at decision time (HKD)")
    position_count: int = Field(..., description="Number of positions")
    recommendation_count: int = Field(..., description="Number of recommendations")
    recommendations: List[HKStrategyAIRecommendation] = Field([], description="AI recommendations")


# ============================================
# Response Types
# ============================================

HKStockStrategiesListResponse = SuccessResponse[List[HKStockStrategyInfo]]
HKStockStrategyDetailResponse = SuccessResponse[HKStockStrategyDetail]
HKStrategyPositionsResponse = SuccessResponse[List[HKStrategyPosition]]
HKStrategyTradesResponse = SuccessResponse[List[HKStrategyTrade]]
HKStrategyPerformanceResponse = SuccessResponse[List[HKStrategyPerformancePoint]]
HKStrategyAIDecisionsResponse = SuccessResponse[List[HKStrategyAIDecision]]

