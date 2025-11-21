"""HK Stock Trading API routes: positions, trades, portfolio value"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading
from stockbuddy.server.api.schemas.base import SuccessResponse

logger = logging.getLogger(__name__)


# ============================================
# Request Schemas
# ============================================

class ExecuteTradeRequest(BaseModel):
    """Request to execute a trade"""
    symbol: str = Field(..., description="Stock symbol (e.g. 00700 or HKEX:00700)")
    side: str = Field(..., description="Trade side: BUY or SELL")
    lots: int = Field(..., gt=0, description="Number of lots to trade")


# ============================================
# Response Schemas
# ============================================

class HKStockPosition(BaseModel):
    """HK stock position data"""
    symbol: str = Field(..., description="Stock symbol (e.g. HKEX:00700)")
    quantity: int = Field(..., description="Position quantity (shares)")
    avg_price: float = Field(..., description="Average entry price (HKD)")
    current_price: float = Field(..., description="Current market price (HKD)")
    market_value: float = Field(..., description="Current market value (HKD)")
    cost_basis: float = Field(..., description="Total cost basis (HKD)")
    unrealized_pnl: float = Field(..., description="Unrealized P&L (HKD)")
    unrealized_pnl_pct: float = Field(..., description="Unrealized P&L percentage")
    lot_size: int = Field(..., description="Lot size for this stock")
    lots: int = Field(..., description="Number of lots")


class HKStockTrade(BaseModel):
    """HK stock trade record"""
    trade_id: str = Field(..., description="Trade ID")
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="Trade side (BUY/SELL)")
    quantity: int = Field(..., description="Trade quantity (shares)")
    price: float = Field(..., description="Execution price (HKD)")
    total_value: float = Field(..., description="Total trade value (HKD)")
    fees: float = Field(..., description="Total fees paid (HKD)")
    timestamp: datetime = Field(..., description="Trade timestamp")
    status: str = Field(..., description="Trade status")


class HKStockPortfolioSummary(BaseModel):
    """HK stock portfolio summary"""
    total_cash: float = Field(..., description="Available cash (HKD)")
    total_market_value: float = Field(..., description="Total position market value (HKD)")
    total_assets: float = Field(..., description="Total assets (cash + positions)")
    total_pnl: float = Field(..., description="Total unrealized P&L (HKD)")
    total_pnl_pct: float = Field(..., description="Total P&L percentage")
    position_count: int = Field(..., description="Number of open positions")


class HKPortfolioValuePoint(BaseModel):
    """Portfolio value at a point in time"""
    timestamp: datetime = Field(..., description="Timestamp")
    total_value: float = Field(..., description="Total portfolio value (HKD)")
    cash: float = Field(..., description="Cash balance (HKD)")
    positions_value: float = Field(..., description="Positions market value (HKD)")


# ============================================
# Response Types
# ============================================

HKStockPositionsResponse = SuccessResponse[List[HKStockPosition]]
HKStockTradesResponse = SuccessResponse[List[HKStockTrade]]
HKStockPortfolioResponse = SuccessResponse[HKStockPortfolioSummary]
HKPortfolioValueHistoryResponse = SuccessResponse[List[HKPortfolioValuePoint]]


# ============================================
# Router
# ============================================

# Global exchange instance for Backend UI (created on demand)
_ui_exchange: Optional[HKStockPaperTrading] = None


def get_ui_exchange() -> HKStockPaperTrading:
    """Get or create UI exchange instance"""
    global _ui_exchange
    if _ui_exchange is None:
        _ui_exchange = HKStockPaperTrading(initial_balance=1000000.0)
        logger.info("Created HK Stock Paper Trading exchange for UI")
    return _ui_exchange


def create_hk_stock_router() -> APIRouter:
    """Create HK stock trading router"""
    
    router = APIRouter(prefix="/hk-stock", tags=["HK Stock"])
    
    @router.post(
        "/trade",
        response_model=SuccessResponse[HKStockTrade],
        summary="Execute HK stock trade",
        description="Execute a buy or sell trade for HK stocks"
    )
    async def execute_trade(request: ExecuteTradeRequest) -> SuccessResponse[HKStockTrade]:
        """Execute a trade"""
        try:
            exchange = get_ui_exchange()
            
            # Normalize symbol (add HKEX: prefix if not present)
            symbol = request.symbol
            if not symbol.startswith("HKEX:"):
                symbol = f"HKEX:{symbol}"
            
            # Note: HKStockPaperTrading.place_order expects quantity in LOTS, not shares
            # It will internally convert lots to shares using the correct lot size
            
            # Place order
            if request.side.upper() == "BUY":
                order = await exchange.place_order(
                    symbol=symbol,
                    side="buy",
                    quantity=request.lots,  # Pass lots directly
                    price=None,  # None for market price
                    order_type="market"
                )
            elif request.side.upper() == "SELL":
                order = await exchange.place_order(
                    symbol=symbol,
                    side="sell",
                    quantity=request.lots,  # Pass lots directly
                    price=None,  # None for market price
                    order_type="market"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid trade side: {request.side}. Must be BUY or SELL"
                )
            
            # Calculate fees (0.1% trading fee + 0.1% stamp duty for HK stocks)
            trade_value = order.quantity * (order.filled_price or order.price)
            fees = trade_value * 0.002  # 0.2% total fees
            
            # Get order status as string
            order_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
            
            # Create trade response
            trade = HKStockTrade(
                trade_id=order.order_id,
                symbol=order.symbol,
                side=request.side.upper(),
                quantity=order.quantity,
                price=order.filled_price or order.price,
                total_value=trade_value,
                fees=fees,
                timestamp=order.created_at,
                status=order_status
            )
            
            return SuccessResponse.create(
                data=trade,
                msg=f"Trade executed successfully: {request.side} {request.lots} lots of {symbol}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute trade: {str(e)}"
            )
    
    @router.get(
        "/positions",
        response_model=HKStockPositionsResponse,
        summary="Get HK stock positions",
        description="Get all current HK stock positions with P&L"
    )
    async def get_hk_stock_positions() -> HKStockPositionsResponse:
        """Get current HK stock positions with real-time prices"""
        try:
            exchange = get_ui_exchange()
            positions_data = exchange.positions  # Direct access to positions dict
            
            position_list = []
            for symbol, pos_data in positions_data.items():
                quantity = pos_data["quantity"]
                avg_price = pos_data.get("entry_price", pos_data.get("avg_price", 0))
                
                # Get real-time market price
                try:
                    current_price = await exchange.get_current_price(symbol)
                except Exception as e:
                    logger.warning(f"Failed to get current price for {symbol}: {e}, using avg_price")
                    current_price = avg_price
                
                market_value = quantity * current_price
                cost_basis = quantity * avg_price
                unrealized_pnl = market_value - cost_basis
                unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0
                
                lot_size = pos_data.get("lot_size", 100)
                lots = quantity // lot_size
                
                position_list.append(HKStockPosition(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=avg_price,
                    current_price=current_price,
                    market_value=market_value,
                    cost_basis=cost_basis,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    lot_size=lot_size,
                    lots=lots
                ))
            
            return SuccessResponse.create(
                data=position_list,
                msg="Successfully retrieved HK stock positions"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get HK stock positions: {str(e)}"
            )
    
    @router.get(
        "/trades",
        response_model=HKStockTradesResponse,
        summary="Get HK stock trade history",
        description="Get historical trades for HK stocks"
    )
    async def get_hk_stock_trades() -> HKStockTradesResponse:
        """Get HK stock trade history"""
        try:
            exchange = get_ui_exchange()
            
            # Get order history
            orders = exchange.orders  # This is a dict: {order_id: Order}
            
            trade_list = []
            for order in orders.values():  # Iterate over Order objects, not keys
                # order.status is an OrderStatus enum, need to get its value
                order_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
                
                if order_status == "filled":
                    trade_value = order.quantity * (order.filled_price or order.price)
                    fees = trade_value * 0.002  # 0.2% total fees
                    
                    trade_list.append(HKStockTrade(
                        trade_id=order.order_id,
                        symbol=order.symbol,
                        side=order.side.upper(),
                        quantity=order.quantity,
                        price=order.filled_price or order.price,
                        total_value=trade_value,
                        fees=fees,
                        timestamp=order.created_at,
                        status=order_status
                    ))
            
            # Sort by timestamp descending
            trade_list.sort(key=lambda x: x.timestamp, reverse=True)
            
            return SuccessResponse.create(
                data=trade_list,
                msg="Successfully retrieved HK stock trade history"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get HK stock trades: {str(e)}"
            )
    
    @router.get(
        "/portfolio",
        response_model=HKStockPortfolioResponse,
        summary="Get HK stock portfolio summary",
        description="Get portfolio summary including cash, positions value, and P&L"
    )
    async def get_hk_portfolio_summary() -> HKStockPortfolioResponse:
        """Get HK stock portfolio summary"""
        try:
            exchange = get_ui_exchange()
            
            # Get balance
            total_cash = exchange.balance
            
            # Calculate positions value with real-time prices
            positions = exchange.positions  # Direct access
            total_market_value = 0.0
            total_cost_basis = 0.0
            
            for symbol, pos_data in positions.items():
                quantity = pos_data["quantity"]
                avg_price = pos_data.get("entry_price", pos_data.get("avg_price", 0))
                
                # Get real-time market price
                try:
                    current_price = await exchange.get_current_price(symbol)
                except Exception as e:
                    logger.warning(f"Failed to get current price for {symbol}: {e}, using avg_price")
                    current_price = avg_price
                
                market_value = quantity * current_price
                cost_basis = quantity * avg_price
                
                total_market_value += market_value
                total_cost_basis += cost_basis
            
            total_assets = total_cash + total_market_value
            total_pnl = total_market_value - total_cost_basis
            total_pnl_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
            
            summary = HKStockPortfolioSummary(
                total_cash=total_cash,
                total_market_value=total_market_value,
                total_assets=total_assets,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                position_count=len(positions)
            )
            
            return SuccessResponse.create(
                data=summary,
                msg="Successfully retrieved portfolio summary"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get portfolio summary: {str(e)}"
            )
    
    @router.get(
        "/portfolio/history",
        response_model=HKPortfolioValueHistoryResponse,
        summary="Get portfolio value history",
        description="Get historical portfolio value over time"
    )
    async def get_portfolio_value_history() -> HKPortfolioValueHistoryResponse:
        """Get portfolio value history with real-time prices"""
        try:
            exchange = get_ui_exchange()
            
            # Get history from exchange
            history = exchange.portfolio_history if hasattr(exchange, 'portfolio_history') else []
            
            # Convert to response format with real-time market value calculation
            history_points = []
            for snapshot in history:
                history_points.append({
                    "timestamp": snapshot["timestamp"],
                    "total_value": snapshot["total_value"],
                    "cash": snapshot.get("cash", 0),
                    "positions_value": snapshot.get("positions_value", 0)
                })
            
            return SuccessResponse.create(
                data=history_points,
                msg=f"Successfully retrieved {len(history_points)} portfolio value history points"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get portfolio value history: {str(e)}"
            )
    
    return router

