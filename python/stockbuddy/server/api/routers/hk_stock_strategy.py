"""HK Stock Strategy API Router"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from stockbuddy.agents.auto_trading_agent.hk_strategy_engine import get_strategy_manager
from stockbuddy.server.api.schemas.hk_stock_strategy import (
    CreateHKStockStrategyRequest,
    HKStockStrategiesListResponse,
    HKStockStrategyDetail,
    HKStockStrategyDetailResponse,
    HKStockStrategyInfo,
    HKStrategyAIDecision,
    HKStrategyAIDecisionsResponse,
    HKStrategyAIRecommendation,
    HKStrategyPerformancePoint,
    HKStrategyPerformanceResponse,
    HKStrategyPosition,
    HKStrategyPositionsResponse,
    HKStrategyTrade,
    HKStrategyTradesResponse,
    UpdateHKStockStrategyRequest,
)

logger = logging.getLogger(__name__)


def create_hk_strategy_router() -> APIRouter:
    """Create and configure the HK stock strategy router"""
    
    router = APIRouter(
        prefix="/hk-stock-strategies",
        tags=["hk-stock-strategies"],
        responses={404: {"description": "Not found"}},
    )
    
    @router.post(
        "/",
        response_model=HKStockStrategyDetailResponse,
        summary="Create HK stock trading strategy",
        description="Create a new HK stock trading strategy in virtual market mode",
    )
    async def create_strategy(
        request: CreateHKStockStrategyRequest,
    ) -> HKStockStrategyDetailResponse:
        """Create a new HK stock trading strategy"""
        try:
            manager = get_strategy_manager()
            
            # Create strategy
            strategy = manager.create_strategy(
                strategy_name=request.strategy_name,
                symbols=request.symbols,
                initial_capital=request.initial_capital,
                strategy_prompt=request.strategy_prompt,
                max_position_size=request.max_position_size,
                max_positions=request.max_positions,
                rebalance_interval=request.rebalance_interval,
            )
            
            # Start strategy
            await strategy.start()
            
            # Get initial portfolio
            portfolio = await strategy.get_portfolio_summary()
            
            # Build response
            detail = HKStockStrategyDetail(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                symbols=strategy.symbols,
                status=strategy.status,
                initial_capital=strategy.initial_capital,
                current_value=portfolio["current_value"],
                total_pnl=portfolio["total_pnl"],
                total_pnl_pct=portfolio["total_pnl_pct"],
                position_count=portfolio["position_count"],
                trade_count=portfolio["trade_count"],
                strategy_prompt=strategy.strategy_prompt,
                max_position_size=strategy.max_position_size,
                max_positions=strategy.max_positions,
                rebalance_interval=strategy.rebalance_interval,
                created_at=strategy.created_at,
                updated_at=strategy.created_at,
                last_rebalance=strategy.last_rebalance,
            )
            
            return HKStockStrategyDetailResponse(
                success=True,
                message="Strategy created successfully",
                data=detail,
            )
            
        except Exception as e:
            logger.error(f"Error creating HK stock strategy: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/",
        response_model=HKStockStrategiesListResponse,
        summary="List HK stock strategies",
        description="Get list of all HK stock trading strategies",
    )
    async def list_strategies(
        status: Optional[str] = Query(None, description="Filter by status"),
    ) -> HKStockStrategiesListResponse:
        """List all HK stock strategies"""
        try:
            manager = get_strategy_manager()
            strategies = manager.list_strategies()
            
            # Filter by status if provided
            if status:
                strategies = [s for s in strategies if s.status == status]
            
            # Build response list
            strategies_list = []
            for strategy in strategies:
                portfolio = await strategy.get_portfolio_summary()
                
                info = HKStockStrategyInfo(
                    strategy_id=strategy.strategy_id,
                    strategy_name=strategy.strategy_name,
                    symbols=strategy.symbols,
                    status=strategy.status,
                    initial_capital=strategy.initial_capital,
                    current_value=portfolio["current_value"],
                    total_pnl=portfolio["total_pnl"],
                    total_pnl_pct=portfolio["total_pnl_pct"],
                    position_count=portfolio["position_count"],
                    trade_count=portfolio["trade_count"],
                    created_at=strategy.created_at,
                    updated_at=strategy.last_rebalance or strategy.created_at,
                )
                strategies_list.append(info)
            
            return HKStockStrategiesListResponse(
                success=True,
                message=f"Found {len(strategies_list)} strategies",
                data=strategies_list,
            )
            
        except Exception as e:
            logger.error(f"Error listing HK stock strategies: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/{strategy_id}",
        response_model=HKStockStrategyDetailResponse,
        summary="Get strategy details",
        description="Get detailed information about a specific HK stock strategy",
    )
    async def get_strategy(strategy_id: str) -> HKStockStrategyDetailResponse:
        """Get strategy details"""
        try:
            manager = get_strategy_manager()
            strategy = manager.get_strategy(strategy_id)
            
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            portfolio = await strategy.get_portfolio_summary()
            
            detail = HKStockStrategyDetail(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                symbols=strategy.symbols,
                status=strategy.status,
                initial_capital=strategy.initial_capital,
                current_value=portfolio["current_value"],
                total_pnl=portfolio["total_pnl"],
                total_pnl_pct=portfolio["total_pnl_pct"],
                position_count=portfolio["position_count"],
                trade_count=portfolio["trade_count"],
                strategy_prompt=strategy.strategy_prompt,
                max_position_size=strategy.max_position_size,
                max_positions=strategy.max_positions,
                rebalance_interval=strategy.rebalance_interval,
                created_at=strategy.created_at,
                updated_at=strategy.last_rebalance or strategy.created_at,
                last_rebalance=strategy.last_rebalance,
            )
            
            return HKStockStrategyDetailResponse(
                success=True,
                message="Strategy details retrieved",
                data=detail,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting strategy details: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.patch(
        "/{strategy_id}",
        response_model=HKStockStrategyDetailResponse,
        summary="Update strategy",
        description="Update strategy parameters or status",
    )
    async def update_strategy(
        strategy_id: str,
        request: UpdateHKStockStrategyRequest,
    ) -> HKStockStrategyDetailResponse:
        """Update strategy"""
        try:
            manager = get_strategy_manager()
            strategy = manager.get_strategy(strategy_id)
            
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            # Update status
            if request.status:
                if request.status == "stopped" and strategy.status == "running":
                    await strategy.stop()
                elif request.status == "running" and strategy.status == "stopped":
                    await strategy.start()
            
            # Update parameters
            if request.max_position_size is not None:
                strategy.max_position_size = request.max_position_size
            if request.max_positions is not None:
                strategy.max_positions = request.max_positions
            
            # Get updated info
            portfolio = await strategy.get_portfolio_summary()
            
            detail = HKStockStrategyDetail(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                symbols=strategy.symbols,
                status=strategy.status,
                initial_capital=strategy.initial_capital,
                current_value=portfolio["current_value"],
                total_pnl=portfolio["total_pnl"],
                total_pnl_pct=portfolio["total_pnl_pct"],
                position_count=portfolio["position_count"],
                trade_count=portfolio["trade_count"],
                strategy_prompt=strategy.strategy_prompt,
                max_position_size=strategy.max_position_size,
                max_positions=strategy.max_positions,
                rebalance_interval=strategy.rebalance_interval,
                created_at=strategy.created_at,
                updated_at=strategy.last_rebalance or strategy.created_at,
                last_rebalance=strategy.last_rebalance,
            )
            
            return HKStockStrategyDetailResponse(
                success=True,
                message="Strategy updated successfully",
                data=detail,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating strategy: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/{strategy_id}/positions",
        response_model=HKStrategyPositionsResponse,
        summary="Get strategy positions",
        description="Get current positions of a strategy",
    )
    async def get_strategy_positions(
        strategy_id: str,
    ) -> HKStrategyPositionsResponse:
        """Get strategy positions"""
        try:
            manager = get_strategy_manager()
            strategy = manager.get_strategy(strategy_id)
            
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            positions_data = await strategy.get_positions()
            
            positions = [
                HKStrategyPosition(**pos) for pos in positions_data
            ]
            
            return HKStrategyPositionsResponse(
                success=True,
                message=f"Found {len(positions)} positions",
                data=positions,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting strategy positions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/{strategy_id}/trades",
        response_model=HKStrategyTradesResponse,
        summary="Get strategy trades",
        description="Get trade history of a strategy",
    )
    async def get_strategy_trades(
        strategy_id: str,
        limit: Optional[int] = Query(100, description="Maximum number of trades to return"),
    ) -> HKStrategyTradesResponse:
        """Get strategy trade history"""
        try:
            manager = get_strategy_manager()
            strategy = manager.get_strategy(strategy_id)
            
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            trades_data = await strategy.get_trades(limit=limit)
            
            trades = [
                HKStrategyTrade(**trade) for trade in trades_data
            ]
            
            return HKStrategyTradesResponse(
                success=True,
                message=f"Found {len(trades)} trades",
                data=trades,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting strategy trades: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/{strategy_id}/performance",
        response_model=HKStrategyPerformanceResponse,
        summary="Get strategy performance",
        description="Get performance history of a strategy",
    )
    async def get_strategy_performance(
        strategy_id: str,
        limit: Optional[int] = Query(1000, description="Maximum number of data points"),
    ) -> HKStrategyPerformanceResponse:
        """Get strategy performance history"""
        try:
            manager = get_strategy_manager()
            strategy = manager.get_strategy(strategy_id)
            
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            performance_data = strategy.performance_history
            
            # Limit data points
            if limit and len(performance_data) > limit:
                performance_data = performance_data[-limit:]
            
            performance = [
                HKStrategyPerformancePoint(**point) for point in performance_data
            ]
            
            return HKStrategyPerformanceResponse(
                success=True,
                message=f"Found {len(performance)} data points",
                data=performance,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting strategy performance: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/{strategy_id}/ai-decisions",
        response_model=HKStrategyAIDecisionsResponse,
        summary="Get AI decisions",
        description="Get AI decision history including recommendations and execution results",
    )
    async def get_strategy_ai_decisions(
        strategy_id: str,
        limit: Optional[int] = Query(50, description="Maximum number of decisions to return"),
    ) -> HKStrategyAIDecisionsResponse:
        """Get AI decision history"""
        try:
            manager = get_strategy_manager()
            strategy = manager.get_strategy(strategy_id)
            
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            decisions_data = await strategy.get_ai_decisions(limit=limit)
            
            # Convert to response schema
            decisions = []
            for decision_data in decisions_data:
                recommendations = [
                    HKStrategyAIRecommendation(**rec) for rec in decision_data.get("recommendations", [])
                ]
                
                decision = HKStrategyAIDecision(
                    timestamp=decision_data["timestamp"],
                    portfolio_value=decision_data["portfolio_value"],
                    cash=decision_data["cash"],
                    position_count=decision_data["position_count"],
                    recommendation_count=decision_data["recommendation_count"],
                    recommendations=recommendations,
                )
                decisions.append(decision)
            
            return HKStrategyAIDecisionsResponse(
                success=True,
                message=f"Found {len(decisions)} AI decisions",
                data=decisions,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting AI decisions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    return router

