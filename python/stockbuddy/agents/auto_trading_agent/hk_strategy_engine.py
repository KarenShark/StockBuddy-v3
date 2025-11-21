"""HK Stock Strategy Execution Engine

This module provides a lightweight strategy execution engine for HK stocks,
running in virtual/paper trading mode for strategy testing and simulation.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from stockbuddy.agents.auto_trading_agent.ai_strategy_analyzer import AIStrategyAnalyzer
from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading

logger = logging.getLogger(__name__)


class HKStockStrategy:
    """
    HK Stock Trading Strategy
    
    Manages a single trading strategy for HK stocks with:
    - Virtual portfolio tracking
    - Periodic rebalancing
    - Position and trade history
    - Performance metrics
    """
    
    def __init__(
        self,
        strategy_id: str,
        strategy_name: str,
        symbols: List[str],
        initial_capital: float,
        strategy_prompt: str,
        max_position_size: float = 0.3,
        max_positions: int = 5,
        rebalance_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize HK Stock Strategy
        
        Args:
            strategy_id: Unique strategy identifier
            strategy_name: User-friendly strategy name
            symbols: List of HK stock symbols to trade
            initial_capital: Starting capital in HKD
            strategy_prompt: Strategy description/logic
            max_position_size: Max position size as % of capital (0-1)
            max_positions: Maximum number of concurrent positions
            rebalance_interval: Rebalance frequency in seconds
        """
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.strategy_prompt = strategy_prompt
        self.max_position_size = max_position_size
        self.max_positions = max_positions
        self.rebalance_interval = rebalance_interval
        
        # Initialize paper trading exchange
        self.exchange = HKStockPaperTrading(initial_balance=initial_capital)
        
        # Initialize AI strategy analyzer
        self.ai_analyzer = AIStrategyAnalyzer()
        
        # Strategy state
        self.status = "running"  # running, stopped, error
        self.created_at = datetime.now(timezone.utc)
        self.last_rebalance: Optional[datetime] = None
        self.trades: List[Dict[str, Any]] = []
        self.performance_history: List[Dict[str, Any]] = []
        self.ai_decisions: List[Dict[str, Any]] = []  # AI decision history
        
        # Execution task
        self._task: Optional[asyncio.Task] = None
        
        logger.info(
            f"📊 HK Stock Strategy created: {strategy_name} (ID: {strategy_id})"
        )
        logger.info(f"  Symbols: {', '.join(symbols)}")
        logger.info(f"  Initial Capital: HKD ${initial_capital:,.2f}")
        logger.info(f"  Rebalance Interval: {rebalance_interval}s")
    
    async def start(self):
        """Start strategy execution loop"""
        if self._task and not self._task.done():
            logger.warning(f"Strategy {self.strategy_id} is already running")
            return
        
        self.status = "running"
        self._task = asyncio.create_task(self._execution_loop())
        logger.info(f"✅ Strategy {self.strategy_name} started")
    
    async def stop(self):
        """Stop strategy execution"""
        self.status = "stopped"
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"🛑 Strategy {self.strategy_name} stopped")
    
    async def _execution_loop(self):
        """Main strategy execution loop"""
        try:
            while self.status == "running":
                try:
                    await self._rebalance()
                    await self._record_performance()
                    await asyncio.sleep(self.rebalance_interval)
                except Exception as e:
                    logger.error(
                        f"Error in strategy {self.strategy_name} execution: {e}",
                        exc_info=True,
                    )
                    self.status = "error"
                    break
        except asyncio.CancelledError:
            logger.info(f"Strategy {self.strategy_name} execution cancelled")
            raise
    
    async def _rebalance(self):
        """Execute rebalancing logic with AI-powered decision making
        
        Process:
        1. Get current portfolio and positions
        2. Call AI analyzer for trading recommendations
        3. Execute recommended trades
        4. Log results
        """
        logger.info(f"🔄 Rebalancing strategy {self.strategy_name}")
        
        # Record rebalance time
        self.last_rebalance = datetime.now(timezone.utc)
        
        # Get current portfolio status
        portfolio = await self.get_portfolio_summary()
        current_positions = await self.get_positions()
        
        logger.info(
            f"  Portfolio Value: HKD ${portfolio['current_value']:,.2f} "
            f"(P&L: {portfolio['total_pnl_pct']:+.2f}%)"
        )
        logger.info(f"  Cash: HKD ${portfolio['cash']:,.2f}")
        logger.info(f"  Open Positions: {portfolio['position_count']}/{self.max_positions}")
        
        # Get AI recommendations
        try:
            recommendations = await self.ai_analyzer.analyze_and_recommend(
                strategy_prompt=self.strategy_prompt,
                symbols=self.symbols,
                portfolio=portfolio,
                current_positions=current_positions,
                max_position_size=self.max_position_size,
                max_positions=self.max_positions,
            )
            
            # Record AI decision (even if no recommendations)
            decision_record = {
                "timestamp": datetime.now(timezone.utc),
                "portfolio_value": portfolio["current_value"],
                "cash": portfolio["cash"],
                "position_count": portfolio["position_count"],
                "recommendations": [
                    {
                        "symbol": rec.symbol,
                        "action": rec.action,
                        "lots": rec.lots,
                        "reason": rec.reason,
                        "confidence": rec.confidence,
                        "target_price": getattr(rec, "target_price", None),
                    }
                    for rec in (recommendations or [])
                ],
                "recommendation_count": len(recommendations) if recommendations else 0,
            }
            self.ai_decisions.append(decision_record)
            
            # Keep only last 100 AI decisions
            if len(self.ai_decisions) > 100:
                self.ai_decisions = self.ai_decisions[-100:]
            
            if not recommendations:
                logger.info("  No trading recommendations from AI")
                return True
            
            # Execute recommended trades
            trades_executed = 0
            for rec in recommendations:
                logger.info(f"  AI Recommendation: {rec.action} {rec.lots} lots of {rec.symbol}")
                logger.info(f"    Reason: {rec.reason}")
                logger.info(f"    Confidence: {rec.confidence:.0%}")
                
                # Execute the trade
                trade = await self.execute_trade(
                    symbol=rec.symbol,
                    side=rec.action,
                    lots=rec.lots,
                    reason=rec.reason,
                )
                
                if trade:
                    trades_executed += 1
                    logger.info(f"  ✅ Trade executed successfully")
                    # Update decision record with execution result
                    for i, rec_data in enumerate(decision_record["recommendations"]):
                        if rec_data["symbol"] == rec.symbol:
                            decision_record["recommendations"][i]["executed"] = True
                            decision_record["recommendations"][i]["trade_id"] = trade.get("trade_id")
                else:
                    logger.warning(f"  ❌ Trade failed")
                    # Update decision record with failure
                    for i, rec_data in enumerate(decision_record["recommendations"]):
                        if rec_data["symbol"] == rec.symbol:
                            decision_record["recommendations"][i]["executed"] = False
            
            logger.info(f"  Executed {trades_executed}/{len(recommendations)} recommended trades")
            
        except Exception as e:
            logger.error(f"Error during rebalancing: {e}", exc_info=True)
            return False
        
        return True
    
    async def _record_performance(self):
        """Record current performance snapshot"""
        portfolio = await self.get_portfolio_summary()
        
        point = {
            "timestamp": datetime.now(timezone.utc),
            "portfolio_value": portfolio["current_value"],
            "cash": portfolio["cash"],
            "positions_value": portfolio["positions_value"],
            "pnl": portfolio["total_pnl"],
            "pnl_pct": portfolio["total_pnl_pct"],
        }
        
        self.performance_history.append(point)
        
        # Keep only last 1000 points
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    async def execute_trade(
        self, symbol: str, side: str, lots: int, reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a trade
        
        Args:
            symbol: Stock symbol (e.g., "00700")
            side: "BUY" or "SELL"
            lots: Number of lots to trade
            reason: Optional reason/signal for the trade
        
        Returns:
            Trade record or None if failed
        """
        try:
            logger.info(f"🔄 Executing trade: {side} {lots} lots of {symbol}")
            
            # Place order through exchange
            order = await self.exchange.place_order(
                symbol=symbol,
                side=side.lower(),
                quantity=lots,  # HKStockPaperTrading expects lots
                order_type="market",
            )
            
            if not order:
                logger.warning(f"❌ Order creation failed: {symbol} {side} {lots} lots")
                return None
            
            if order.status != "filled":
                logger.warning(f"❌ Order not filled: {symbol} {side} {lots} lots - Status: {order.status}")
                return None
            
            # Calculate fees (already included in exchange)
            lot_size = self.exchange.get_lot_size(symbol)
            shares = lots * lot_size
            
            # Record trade
            trade = {
                "trade_id": order.order_id,
                "symbol": symbol,
                "side": side.upper(),
                "quantity": shares,
                "lots": lots,
                "price": order.filled_price or order.price,
                "total_value": (order.filled_price or order.price) * shares,
                "fees": 0.0,  # Fees are handled by exchange internally
                "timestamp": datetime.now(timezone.utc),
                "reason": reason,
            }
            
            self.trades.append(trade)
            
            logger.info(
                f"✅ Trade executed: {side} {lots} lots of {symbol} @ "
                f"HKD ${trade['price']:.2f}"
            )
            
            return trade
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            logger.info(f"🔍 Strategy {self.strategy_name} getting positions from exchange")
            exchange_positions = await self.exchange.get_open_positions()
            
            logger.info(f"🔍 Exchange returned {len(exchange_positions)} positions")
            
            positions = []
            for symbol, pos_data in exchange_positions.items():
                logger.info(f"🔍 Processing position: {symbol} - {pos_data}")
                
                # Fix: access 'entry_price' not 'avg_price'
                quantity = pos_data.get("quantity", 0)
                if quantity == 0:
                    logger.info(f"🔍 Skipping {symbol} - zero quantity")
                    continue
                
                lot_size = self.exchange.get_lot_size(symbol)
                current_price = await self.exchange.get_current_price(symbol)
                
                lots = quantity // lot_size
                avg_price = pos_data.get("entry_price", 0)  # Fix: was 'avg_price'
                cost_basis = quantity * avg_price
                market_value = quantity * current_price
                unrealized_pnl = market_value - cost_basis
                unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0
                
                position = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "lots": lots,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "market_value": market_value,
                    "cost_basis": cost_basis,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_pct": unrealized_pnl_pct,
                }
                positions.append(position)
                logger.info(f"✅ Added position: {symbol} - {lots} lots, value ${market_value:,.2f}")
            
            logger.info(f"✅ Total positions returned: {len(positions)}")
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}", exc_info=True)
            return []
    
    async def get_trades(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade history
        
        Args:
            limit: Maximum number of trades to return (most recent first)
        
        Returns:
            List of trade records
        """
        trades = sorted(self.trades, key=lambda t: t["timestamp"], reverse=True)
        if limit:
            trades = trades[:limit]
        return trades
    
    async def get_ai_decisions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get AI decision history
        
        Args:
            limit: Maximum number of decisions to return (most recent first)
        
        Returns:
            List of AI decision records with recommendations and execution results
        """
        decisions = sorted(self.ai_decisions, key=lambda d: d["timestamp"], reverse=True)
        if limit:
            decisions = decisions[:limit]
        return decisions
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary statistics"""
        try:
            balance = await self.exchange.get_balance()
            cash = balance.get("HKD", self.initial_capital)
            
            positions = await self.get_positions()
            positions_value = sum(p["market_value"] for p in positions)
            
            current_value = cash + positions_value
            total_pnl = current_value - self.initial_capital
            total_pnl_pct = (total_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0.0
            
            return {
                "cash": cash,
                "positions_value": positions_value,
                "current_value": current_value,
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "position_count": len(positions),
                "trade_count": len(self.trades),
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}", exc_info=True)
            return {
                "cash": self.initial_capital,
                "positions_value": 0.0,
                "current_value": self.initial_capital,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "position_count": 0,
                "trade_count": 0,
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary"""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "symbols": self.symbols,
            "status": self.status,
            "initial_capital": self.initial_capital,
            "strategy_prompt": self.strategy_prompt,
            "max_position_size": self.max_position_size,
            "max_positions": self.max_positions,
            "rebalance_interval": self.rebalance_interval,
            "created_at": self.created_at.isoformat(),
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
        }


class HKStrategyManager:
    """Manage multiple HK stock strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, HKStockStrategy] = {}
        logger.info("HK Strategy Manager initialized")
    
    def create_strategy(
        self,
        strategy_name: str,
        symbols: List[str],
        initial_capital: float,
        strategy_prompt: str,
        **kwargs,
    ) -> HKStockStrategy:
        """Create a new strategy"""
        strategy_id = str(uuid.uuid4())
        
        strategy = HKStockStrategy(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbols=symbols,
            initial_capital=initial_capital,
            strategy_prompt=strategy_prompt,
            **kwargs,
        )
        
        self.strategies[strategy_id] = strategy
        logger.info(f"Strategy created: {strategy_name} (ID: {strategy_id})")
        
        return strategy
    
    def get_strategy(self, strategy_id: str) -> Optional[HKStockStrategy]:
        """Get strategy by ID"""
        return self.strategies.get(strategy_id)
    
    def list_strategies(self) -> List[HKStockStrategy]:
        """List all strategies"""
        return list(self.strategies.values())
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start a strategy"""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            logger.error(f"Strategy not found: {strategy_id}")
            return False
        
        await strategy.start()
        return True
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop a strategy"""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            logger.error(f"Strategy not found: {strategy_id}")
            return False
        
        await strategy.stop()
        return True
    
    async def stop_all_strategies(self):
        """Stop all running strategies"""
        for strategy in self.strategies.values():
            if strategy.status == "running":
                await strategy.stop()
        logger.info("All strategies stopped")


# Global strategy manager instance
_strategy_manager: Optional[HKStrategyManager] = None


def get_strategy_manager() -> HKStrategyManager:
    """Get or create global strategy manager"""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = HKStrategyManager()
    return _strategy_manager

