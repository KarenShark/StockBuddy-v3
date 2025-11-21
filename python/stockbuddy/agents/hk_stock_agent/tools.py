"""Tools for HK Stock Trading Agent"""

import json
from typing import Dict, List, Optional

from loguru import logger

from stockbuddy.adapters.assets.manager import get_adapter_manager
from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading
from stockbuddy.agents.auto_trading_agent.hk_stock_market_data import (
    get_hk_stock_market_data_provider,
)

# Global instances (will be initialized by agent)
_exchange: Optional[HKStockPaperTrading] = None
_market_data = None


def initialize_trading_system(exchange: HKStockPaperTrading):
    """Initialize the global trading system instance."""
    global _exchange, _market_data
    _exchange = exchange
    _market_data = get_hk_stock_market_data_provider()
    logger.info("HK Stock trading system initialized")


async def get_hk_stock_price(stock_code: str) -> str:
    """
    Get current real-time price for a Hong Kong stock.
    
    Args:
        stock_code: HK stock code (e.g., "00700", "09988", "00941")
                   Can include HKEX: prefix or just the 5-digit code
    
    Returns:
        JSON string with stock price information
    
    Example:
        get_hk_stock_price("00700") -> returns Tencent's current price
        get_hk_stock_price("HKEX:09988") -> returns Alibaba's current price
    """
    try:
        # Normalize stock code
        if not stock_code.startswith("HKEX:"):
            stock_code = f"HKEX:{stock_code.zfill(5)}"
        
        if not _exchange:
            return json.dumps({"error": "Trading system not initialized"})
        
        price = await _exchange.get_current_price(stock_code)
        
        if price and price > 0:
            result = {
                "symbol": stock_code,
                "price": round(price, 2),
                "currency": "HKD",
                "timestamp": "now",
            }
            logger.info(f"Got price for {stock_code}: ${price:.2f} HKD")
            return json.dumps(result, ensure_ascii=False)
        else:
            return json.dumps({
                "error": f"No price data available for {stock_code}",
                "symbol": stock_code,
            })
    
    except Exception as e:
        logger.error(f"Error getting price for {stock_code}: {e}")
        return json.dumps({"error": str(e), "symbol": stock_code})


async def analyze_hk_stock(stock_code: str, days: int = 60) -> str:
    """
    Analyze a Hong Kong stock with technical indicators and trading signals.
    
    Args:
        stock_code: HK stock code (e.g., "00700", "09988")
        days: Number of days of historical data to analyze (default: 60)
    
    Returns:
        JSON string with comprehensive analysis including:
        - Technical indicators (MA, RSI, MACD, Bollinger Bands)
        - Trading signal (BUY/HOLD/SELL)
        - Confidence level
        - Reasons for the signal
        - AH premium (if applicable)
        - HK Connect flow data
    
    Example:
        analyze_hk_stock("00700", 60) -> returns full analysis for Tencent
    """
    try:
        # Normalize stock code
        if not stock_code.startswith("HKEX:"):
            stock_code = f"HKEX:{stock_code.zfill(5)}"
        
        if not _market_data:
            return json.dumps({"error": "Market data provider not initialized"})
        
        # Generate trading signal
        signal = _market_data.generate_trading_signal(stock_code, days=days)
        
        # Format the response
        result = {
            "symbol": stock_code,
            "signal": signal.get("signal", "HOLD"),
            "confidence": signal.get("confidence", 0.0),
            "reasons": signal.get("reasons", []),
        }
        
        # Add technical indicators if available
        if "indicators" in signal:
            indicators = signal["indicators"]
            result["indicators"] = {
                "current_price": indicators.get("current_price"),
                "ma_20": indicators.get("ma_20"),
                "ma_50": indicators.get("ma_50"),
                "rsi_14": indicators.get("rsi_14"),
                "macd": indicators.get("macd"),
                "macd_signal": indicators.get("macd_signal"),
            }
        
        logger.info(f"Analysis for {stock_code}: {result['signal']} (confidence: {result['confidence']:.2f})")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error analyzing {stock_code}: {e}")
        return json.dumps({"error": str(e), "symbol": stock_code})


async def execute_hk_stock_buy(stock_code: str, lots: int) -> str:
    """
    Execute a buy order for a Hong Kong stock (paper trading).
    
    Args:
        stock_code: HK stock code (e.g., "00700", "09988")
        lots: Number of lots to buy (1 lot = lot_size shares, typically 100)
    
    Returns:
        JSON string with order confirmation details
    
    Example:
        execute_hk_stock_buy("00700", 2) -> buys 2 lots (200 shares) of Tencent
    
    Note:
        This is PAPER TRADING - no real money involved!
        Different stocks have different lot sizes (100, 200, 500, etc.)
    """
    try:
        # Normalize stock code
        if not stock_code.startswith("HKEX:"):
            stock_code = f"HKEX:{stock_code.zfill(5)}"
        
        if not _exchange:
            return json.dumps({"error": "Trading system not initialized"})
        
        # Get lot size
        lot_size = _exchange.get_lot_size(stock_code)
        shares = lots * lot_size
        
        # Get current price
        current_price = await _exchange.get_current_price(stock_code)
        
        if not current_price or current_price <= 0:
            return json.dumps({
                "error": f"Cannot get valid price for {stock_code}",
                "symbol": stock_code,
            })
        
        # Calculate estimated cost
        notional = shares * current_price
        fees = _exchange.calculate_fees(notional, "buy")
        total_cost = notional + fees
        
        # Execute buy
        order = await _exchange.execute_buy(stock_code, quantity=lots, price=None)
        
        if order:
            result = {
                "status": "success",
                "order_id": order.order_id,
                "symbol": stock_code,
                "action": "BUY",
                "lots": lots,
                "shares": shares,
                "lot_size": lot_size,
                "price": round(order.price, 2),
                "total_cost": round(total_cost, 2),
                "fees": round(fees, 2),
                "currency": "HKD",
                "order_status": order.status.value,
            }
            logger.info(f"Buy order executed: {lots} lots of {stock_code} @ ${order.price:.2f}")
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "error": "Order execution failed (insufficient balance or other issue)",
                "symbol": stock_code,
                "attempted_lots": lots,
            })
    
    except Exception as e:
        logger.error(f"Error executing buy for {stock_code}: {e}")
        return json.dumps({"error": str(e), "symbol": stock_code})


async def execute_hk_stock_sell(stock_code: str, lots: int) -> str:
    """
    Execute a sell order for a Hong Kong stock (paper trading).
    
    Args:
        stock_code: HK stock code (e.g., "00700", "09988")
        lots: Number of lots to sell (1 lot = lot_size shares)
    
    Returns:
        JSON string with order confirmation details
    
    Example:
        execute_hk_stock_sell("00700", 1) -> sells 1 lot (100 shares) of Tencent
    
    Note:
        Can only sell stocks you currently hold!
    """
    try:
        # Normalize stock code
        if not stock_code.startswith("HKEX:"):
            stock_code = f"HKEX:{stock_code.zfill(5)}"
        
        if not _exchange:
            return json.dumps({"error": "Trading system not initialized"})
        
        # Check if we have this position
        positions = await _exchange.get_open_positions(stock_code)
        if not positions or stock_code not in positions:
            return json.dumps({
                "error": f"No position found for {stock_code}. Cannot sell.",
                "symbol": stock_code,
            })
        
        # Get lot size
        lot_size = _exchange.get_lot_size(stock_code)
        shares = lots * lot_size
        
        # Check if we have enough shares
        position = positions[stock_code]
        if position["quantity"] < shares:
            return json.dumps({
                "error": f"Insufficient shares. You have {position['quantity']} shares, trying to sell {shares}",
                "symbol": stock_code,
                "available_shares": position["quantity"],
                "attempted_shares": shares,
            })
        
        # Get current price
        current_price = await _exchange.get_current_price(stock_code)
        
        if not current_price or current_price <= 0:
            return json.dumps({
                "error": f"Cannot get valid price for {stock_code}",
                "symbol": stock_code,
            })
        
        # Calculate estimated proceeds
        notional = shares * current_price
        fees = _exchange.calculate_fees(notional, "sell")
        proceeds = notional - fees
        
        # Execute sell
        order = await _exchange.execute_sell(stock_code, quantity=lots, price=None)
        
        if order:
            result = {
                "status": "success",
                "order_id": order.order_id,
                "symbol": stock_code,
                "action": "SELL",
                "lots": lots,
                "shares": shares,
                "lot_size": lot_size,
                "price": round(order.price, 2),
                "proceeds": round(proceeds, 2),
                "fees": round(fees, 2),
                "currency": "HKD",
                "order_status": order.status.value,
            }
            logger.info(f"Sell order executed: {lots} lots of {stock_code} @ ${order.price:.2f}")
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "error": "Order execution failed",
                "symbol": stock_code,
            })
    
    except Exception as e:
        logger.error(f"Error executing sell for {stock_code}: {e}")
        return json.dumps({"error": str(e), "symbol": stock_code})


async def get_hk_portfolio() -> str:
    """
    Get current HK stock portfolio with all positions and account balance.
    
    Returns:
        JSON string with:
        - Current cash balance
        - All open positions with current prices and P&L
        - Total portfolio value
        - Total returns
    
    Example:
        get_hk_portfolio() -> returns complete portfolio status
    """
    try:
        if not _exchange:
            return json.dumps({"error": "Trading system not initialized"})
        
        # Get balance
        balance = await _exchange.get_balance()
        cash = balance.get("HKD", 0)
        
        # Get all positions
        positions = await _exchange.get_open_positions()
        
        position_list = []
        total_position_value = 0
        total_cost = 0
        
        for symbol, pos in positions.items():
            # Get current price
            current_price = await _exchange.get_current_price(symbol)
            
            if current_price and current_price > 0:
                market_value = pos["quantity"] * current_price
                cost_basis = pos["quantity"] * pos["entry_price"]
                pnl = market_value - cost_basis
                pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
                
                total_position_value += market_value
                total_cost += cost_basis
                
                position_list.append({
                    "symbol": symbol,
                    "quantity": pos["quantity"],
                    "entry_price": round(pos["entry_price"], 2),
                    "current_price": round(current_price, 2),
                    "market_value": round(market_value, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                })
        
        total_assets = cash + total_position_value
        total_pnl = total_position_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        result = {
            "cash": round(cash, 2),
            "positions": position_list,
            "position_count": len(position_list),
            "total_position_value": round(total_position_value, 2),
            "total_assets": round(total_assets, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "currency": "HKD",
        }
        
        logger.info(f"Portfolio: {len(position_list)} positions, total value: ${total_assets:,.2f} HKD")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return json.dumps({"error": str(e)})


async def search_hk_stocks(query: str, limit: int = 10) -> str:
    """
    Search for Hong Kong stocks by name or code.
    
    Args:
        query: Search query (company name, stock code, or keywords)
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        JSON string with list of matching stocks
    
    Example:
        search_hk_stocks("tencent") -> finds 00700 Tencent Holdings
        search_hk_stocks("银行") -> finds bank stocks
    """
    try:
        adapter_manager = get_adapter_manager()
        
        from stockbuddy.adapters.assets.types import AssetSearchQuery, AssetType
        
        search_query = AssetSearchQuery(
            query=query,
            asset_types=[AssetType.STOCK],
            limit=limit,
        )
        
        results = adapter_manager.search_assets(search_query)
        
        # Filter for HKEX stocks only
        hk_results = [r for r in results if r.ticker.startswith("HKEX:")]
        
        stock_list = []
        for result in hk_results[:limit]:
            stock_list.append({
                "symbol": result.ticker,
                "name": result.names.get("en") or result.names.get("zh") or "Unknown",
                "exchange": result.exchange.value if hasattr(result.exchange, "value") else str(result.exchange),
            })
        
        response = {
            "query": query,
            "results_count": len(stock_list),
            "stocks": stock_list,
        }
        
        logger.info(f"Search '{query}' found {len(stock_list)} HK stocks")
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error searching stocks for '{query}': {e}")
        return json.dumps({"error": str(e), "query": query})


# Tool definitions for Agno Agent
TOOLS = [
    get_hk_stock_price,
    analyze_hk_stock,
    execute_hk_stock_buy,
    execute_hk_stock_sell,
    get_hk_portfolio,
    search_hk_stocks,
]

