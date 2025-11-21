"""AI-Powered Strategy Analyzer

This module provides AI-driven trading decision making for HK stock strategies.
Uses LLM to analyze market conditions and generate trading recommendations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agno.agent import Agent as AgnoAgent

from stockbuddy.utils import model as model_utils
from stockbuddy.agents.auto_trading_agent.hk_stock_market_data import (
    HKStockMarketDataProvider,
)

logger = logging.getLogger(__name__)


class TradeRecommendation:
    """Trading recommendation from AI analysis"""
    
    def __init__(
        self,
        symbol: str,
        action: str,  # "BUY", "SELL", "HOLD"
        lots: int,
        confidence: float,
        reason: str,
    ):
        self.symbol = symbol
        self.action = action
        self.lots = lots
        self.confidence = confidence
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "lots": self.lots,
            "confidence": self.confidence,
            "reason": self.reason,
        }


class AIStrategyAnalyzer:
    """
    AI-powered strategy analyzer that uses LLM to make trading decisions.
    
    Features:
    - Analyzes current portfolio and market conditions
    - Generates trading recommendations based on strategy prompt
    - Considers risk management and position sizing
    """
    
    def __init__(
        self,
        model_id: str = "google/gemini-2.5-flash",
        provider: str = "openrouter",
    ):
        """Initialize AI strategy analyzer
        
        Args:
            model_id: LLM model ID
            provider: Model provider name
        """
        # Create model using model_utils
        self.model = model_utils.create_model_with_provider(
            provider=provider,
            model_id=model_id,
        )
        self.market_data = HKStockMarketDataProvider()
        logger.info(f"AI Strategy Analyzer initialized with {model_id}")
    
    async def analyze_and_recommend(
        self,
        strategy_prompt: str,
        symbols: List[str],
        portfolio: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
        max_position_size: float,
        max_positions: int,
    ) -> List[TradeRecommendation]:
        """
        Analyze market and generate trading recommendations.
        
        Args:
            strategy_prompt: User's strategy description
            symbols: List of symbols to trade
            portfolio: Current portfolio summary (cash, value, pnl)
            current_positions: Current open positions
            max_position_size: Max position size as % of capital
            max_positions: Max number of concurrent positions
        
        Returns:
            List of trading recommendations
        """
        try:
            # Get current market data for all symbols
            market_data_all = {}
            for symbol in symbols:
                price = await self._get_price(symbol)
                if price:
                    market_data_all[symbol] = {
                        "symbol": symbol,
                        "current_price": price,
                    }
            
            # Build prompt for LLM
            prompt = self._build_analysis_prompt(
                strategy_prompt=strategy_prompt,
                symbols=symbols,
                market_data=market_data_all,
                portfolio=portfolio,
                current_positions=current_positions,
                max_position_size=max_position_size,
                max_positions=max_positions,
            )
            
            logger.info("🤖 Calling AI for trading analysis...")
            logger.debug(f"Prompt:\n{prompt}")
            
            # Wrap model in Agno Agent for consistent invocation
            agent = AgnoAgent(
                model=self.model,
                markdown=False,
                instructions=["You are a professional Hong Kong stock trading analyst."],
            )
            
            # Get AI recommendations
            response = await agent.arun(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"🤖 AI Response:\n{response_text}")
            
            # Parse recommendations
            recommendations = self._parse_recommendations(response_text)
            
            logger.info(f"✅ Generated {len(recommendations)} trading recommendations")
            for rec in recommendations:
                logger.info(f"   {rec.action} {rec.lots} lots of {rec.symbol} (confidence: {rec.confidence:.0%})")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}", exc_info=True)
            return []
    
    async def _get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Ensure symbol has HKEX: prefix
            if not symbol.startswith("HKEX:"):
                symbol = f"HKEX:{symbol}"
            
            return self.market_data.get_current_price(symbol)
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None
    
    def _build_analysis_prompt(
        self,
        strategy_prompt: str,
        symbols: List[str],
        market_data: Dict[str, Dict[str, Any]],
        portfolio: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
        max_position_size: float,
        max_positions: int,
    ) -> str:
        """Build prompt for LLM analysis"""
        
        # Format current positions
        positions_text = "None"
        if current_positions:
            pos_lines = []
            for pos in current_positions:
                pos_lines.append(
                    f"- {pos['symbol']}: {pos['lots']} lots @ HK${pos['avg_price']:.2f}, "
                    f"Current: HK${pos['current_price']:.2f}, "
                    f"P&L: {pos['unrealized_pnl_pct']:+.2f}%"
                )
            positions_text = "\n".join(pos_lines)
        
        # Format market data
        market_text = []
        for symbol, data in market_data.items():
            market_text.append(
                f"- {symbol}: HK${data['current_price']:.2f}"
            )
        market_data_text = "\n".join(market_text) if market_text else "No market data available"
        
        # Calculate available cash and position limits
        available_cash = portfolio['cash']
        current_position_count = len(current_positions)
        max_position_value = portfolio['current_value'] * max_position_size
        
        prompt = f"""You are a professional Hong Kong stock trader managing a virtual trading portfolio.

## Strategy Objective
{strategy_prompt}

## Current Portfolio Status
- Total Value: HK${portfolio['current_value']:,.2f}
- Available Cash: HK${available_cash:,.2f}
- Positions Value: HK${portfolio['positions_value']:,.2f}
- Total P&L: HK${portfolio['total_pnl']:+,.2f} ({portfolio['total_pnl_pct']:+.2f}%)
- Open Positions: {current_position_count}/{max_positions}

## Current Positions
{positions_text}

## Available Stocks and Current Prices
{market_data_text}

## Trading Constraints
- Maximum {max_positions} concurrent positions (currently holding {current_position_count})
- Maximum position size: {max_position_size*100:.0f}% of capital = HK${max_position_value:,.2f}
- Available cash: HK${available_cash:,.2f}
- Trade in LOTS (1 lot = 100 shares for most HK stocks)

## Your Task
Based on the strategy objective and current market conditions, provide trading recommendations in this EXACT JSON format:

```json
{{
  "recommendations": [
    {{
      "symbol": "HKEX:00700",
      "action": "BUY",
      "lots": 5,
      "confidence": 0.8,
      "reason": "Strong momentum and undervalued"
    }},
    {{
      "symbol": "HKEX:09988",
      "action": "HOLD",
      "lots": 0,
      "confidence": 0.6,
      "reason": "Wait for better entry point"
    }}
  ]
}}
```

**Rules:**
1. action must be "BUY", "SELL", or "HOLD"
2. For BUY: only recommend if you have available cash and haven't reached max_positions
3. For SELL: only recommend for stocks we currently hold
4. lots must be a positive integer for BUY/SELL, 0 for HOLD
5. confidence: 0.0 to 1.0 indicating your confidence level
6. Consider the strategy objective when making decisions
7. Be conservative with risk - don't use all available cash at once
8. Provide clear reasoning for each recommendation

Respond ONLY with the JSON object, no other text.
"""
        return prompt
    
    def _parse_recommendations(self, response_text: str) -> List[TradeRecommendation]:
        """Parse AI response into trading recommendations"""
        try:
            # Extract JSON from response (handle markdown code blocks)
            import re
            
            # Try to find JSON in markdown code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find JSON directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    logger.error("No JSON found in AI response")
                    return []
            
            # Parse JSON
            data = json.loads(json_text)
            recommendations = []
            
            for rec_data in data.get("recommendations", []):
                action = rec_data.get("action", "HOLD").upper()
                
                # Skip HOLD recommendations or invalid actions
                if action == "HOLD" or action not in ["BUY", "SELL"]:
                    continue
                
                rec = TradeRecommendation(
                    symbol=rec_data.get("symbol", ""),
                    action=action,
                    lots=int(rec_data.get("lots", 0)),
                    confidence=float(rec_data.get("confidence", 0.0)),
                    reason=rec_data.get("reason", ""),
                )
                
                # Validate recommendation
                if rec.symbol and rec.lots > 0 and rec.action in ["BUY", "SELL"]:
                    recommendations.append(rec)
            
            return recommendations
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text:\n{response_text}")
            return []
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}", exc_info=True)
            return []

