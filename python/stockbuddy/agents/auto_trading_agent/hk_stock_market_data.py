"""Hong Kong Stock Market Data Provider

Provides market data and technical indicators for Hong Kong stocks:
- Real-time prices via AdapterManager
- Technical indicators (MA, RSI, MACD, volume)
- HK-specific indicators (AH premium, HSI correlation, HK Connect flow)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from stockbuddy.adapters.assets.ah_premium_adapter import AHPremiumAdapter
from stockbuddy.adapters.assets.hkconnect_adapter import HKConnectAdapter
from stockbuddy.adapters.assets.manager import get_adapter_manager

logger = logging.getLogger(__name__)


class HKStockMarketDataProvider:
    """
    Market data provider for Hong Kong stocks.
    
    Features:
    - Real-time price data
    - Technical indicators (MA, RSI, MACD, Bollinger Bands)
    - HK-specific data (AH premium, HK Connect flow, HSI correlation)
    """

    def __init__(self):
        """Initialize HK stock market data provider."""
        self.adapter_manager = get_adapter_manager()
        self.ah_premium_adapter = AHPremiumAdapter()
        self.hk_connect_adapter = HKConnectAdapter()
        
        logger.info("HK Stock Market Data Provider initialized")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current real-time price for a HK stock.
        
        Args:
            symbol: Stock symbol in internal format (e.g., "HKEX:00700")
        
        Returns:
            Current price in HKD or None if unavailable
        """
        try:
            # Ensure symbol has HKEX: prefix
            if not symbol.startswith("HKEX:"):
                symbol = f"HKEX:{symbol}"
            
            price_data = self.adapter_manager.get_real_time_price(symbol)
            
            if price_data and price_data.price:
                return float(price_data.price)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    def get_historical_data(
        self,
        symbol: str,
        days: int = 60,
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """
        Get historical price data for technical analysis.
        
        Args:
            symbol: Stock symbol (e.g., "HKEX:00700")
            days: Number of days of historical data
            interval: Data interval (default: "1d")
        
        Returns:
            DataFrame with OHLCV data or None if unavailable
        """
        try:
            # Ensure symbol has HKEX: prefix
            if not symbol.startswith("HKEX:"):
                symbol = f"HKEX:{symbol}"
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            price_list = self.adapter_manager.get_historical_prices(
                symbol, start_date, end_date, interval
            )
            
            if not price_list:
                logger.warning(f"No historical data for {symbol}")
                return None
            
            # Convert to DataFrame
            data = []
            for price in price_list:
                data.append({
                    "timestamp": price.timestamp,
                    "open": price.open_price,
                    "high": price.high_price,
                    "low": price.low_price,
                    "close": price.price,
                    "volume": price.volume,
                })
            
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
            
            logger.debug(f"Got {len(df)} historical data points for {symbol}")
            
            return df
        
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return None

    def calculate_technical_indicators(
        self,
        symbol: str,
        days: int = 60,
    ) -> Optional[Dict]:
        """
        Calculate technical indicators for a HK stock.
        
        Args:
            symbol: Stock symbol
            days: Number of days of data to analyze
        
        Returns:
            Dictionary with technical indicators or None
        """
        try:
            df = self.get_historical_data(symbol, days=days)
            
            if df is None or df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for technical indicators: {symbol}")
                return None
            
            close = df["close"].values
            high = df["high"].values
            low = df["low"].values
            volume = df["volume"].values
            
            # Calculate indicators
            indicators = {}
            
            # Helper function for SMA
            def calculate_sma(data, period):
                if len(data) >= period:
                    return float(pd.Series(data).rolling(window=period).mean().iloc[-1])
                return None
            
            # Moving Averages
            indicators["ma_5"] = calculate_sma(close, 5)
            indicators["ma_10"] = calculate_sma(close, 10)
            indicators["ma_20"] = calculate_sma(close, 20)
            indicators["ma_50"] = calculate_sma(close, 50)
            
            # RSI (Relative Strength Index)
            def calculate_rsi(data, period=14):
                if len(data) < period + 1:
                    return None
                delta = pd.Series(data).diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return float(rsi.iloc[-1])
            
            indicators["rsi_14"] = calculate_rsi(close, 14)
            
            # MACD
            def calculate_macd(data, fast=12, slow=26, signal=9):
                if len(data) < slow + signal:
                    return None, None, None
                prices = pd.Series(data)
                ema_fast = prices.ewm(span=fast, adjust=False).mean()
                ema_slow = prices.ewm(span=slow, adjust=False).mean()
                macd_line = ema_fast - ema_slow
                signal_line = macd_line.ewm(span=signal, adjust=False).mean()
                histogram = macd_line - signal_line
                return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])
            
            if len(close) >= 34:
                macd, signal, hist = calculate_macd(close)
                indicators["macd"] = macd
                indicators["macd_signal"] = signal
                indicators["macd_hist"] = hist
            else:
                indicators["macd"] = None
                indicators["macd_signal"] = None
                indicators["macd_hist"] = None
            
            # Bollinger Bands
            def calculate_bbands(data, period=20, std_dev=2):
                if len(data) < period:
                    return None, None, None
                prices = pd.Series(data)
                middle = prices.rolling(window=period).mean()
                std = prices.rolling(window=period).std()
                upper = middle + (std * std_dev)
                lower = middle - (std * std_dev)
                return float(upper.iloc[-1]), float(middle.iloc[-1]), float(lower.iloc[-1])
            
            if len(close) >= 20:
                upper, middle, lower = calculate_bbands(close)
                indicators["bb_upper"] = upper
                indicators["bb_middle"] = middle
                indicators["bb_lower"] = lower
            else:
                indicators["bb_upper"] = None
                indicators["bb_middle"] = None
                indicators["bb_lower"] = None
            
            # Volume indicators
            indicators["volume_ma_20"] = calculate_sma(volume, 20)
            
            # Current price
            indicators["current_price"] = close[-1]
            
            # Price change
            if len(close) >= 2:
                indicators["price_change_pct"] = ((close[-1] - close[-2]) / close[-2]) * 100
            else:
                indicators["price_change_pct"] = 0.0
            
            logger.debug(f"Calculated technical indicators for {symbol}")
            
            return indicators
        
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators for {symbol}: {e}")
            return None

    def get_ah_premium(self, symbol: str) -> Optional[Dict]:
        """
        Get AH stock premium data for a HK stock (if applicable).
        
        Args:
            symbol: HK stock symbol (e.g., "HKEX:00939")
        
        Returns:
            AH premium data or None if not an AH stock
        """
        try:
            # Clean symbol
            if symbol.startswith("HKEX:"):
                symbol = symbol.replace("HKEX:", "")
            
            premium_data = self.ah_premium_adapter.calculate_premium(symbol)
            
            if premium_data:
                logger.debug(f"AH premium for {symbol}: {premium_data['premium_rate']:.2f}%")
            
            return premium_data
        
        except Exception as e:
            logger.error(f"Failed to get AH premium for {symbol}: {e}")
            return None

    def get_hk_connect_flow(self, days: int = 5) -> Optional[Dict]:
        """
        Get Hong Kong Connect (港股通) capital flow data.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Capital flow data or None if unavailable
        """
        try:
            flow_data = self.hk_connect_adapter.get_southbound_flow(days=days)
            
            if flow_data and flow_data.get("status") == "success":
                logger.debug(f"HK Connect flow ({days}d): {flow_data['total_inflow']:.2f}亿元")
                return flow_data
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get HK Connect flow: {e}")
            return None

    def generate_trading_signal(
        self,
        symbol: str,
        days: int = 60,
    ) -> Dict:
        """
        Generate a comprehensive trading signal for a HK stock.
        
        Args:
            symbol: Stock symbol
            days: Days of data to analyze
        
        Returns:
            Dictionary with signal analysis
        """
        try:
            # Get technical indicators
            indicators = self.calculate_technical_indicators(symbol, days=days)
            
            if not indicators:
                return {
                    "symbol": symbol,
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "reason": "Insufficient data",
                }
            
            # Simple signal logic (can be enhanced with ML later)
            signal = "HOLD"
            confidence = 0.5
            reasons = []
            
            current_price = indicators["current_price"]
            rsi = indicators.get("rsi_14")
            macd_hist = indicators.get("macd_hist")
            ma_20 = indicators.get("ma_20")
            
            # RSI-based signals
            if rsi:
                if rsi < 30:
                    signal = "BUY"
                    confidence += 0.2
                    reasons.append(f"RSI oversold ({rsi:.1f})")
                elif rsi > 70:
                    signal = "SELL"
                    confidence += 0.2
                    reasons.append(f"RSI overbought ({rsi:.1f})")
            
            # MACD-based signals
            if macd_hist:
                if macd_hist > 0 and signal != "SELL":
                    if signal == "HOLD":
                        signal = "BUY"
                    confidence += 0.15
                    reasons.append("MACD bullish")
                elif macd_hist < 0 and signal != "BUY":
                    if signal == "HOLD":
                        signal = "SELL"
                    confidence += 0.15
                    reasons.append("MACD bearish")
            
            # MA-based signals
            if ma_20:
                if current_price > ma_20 and signal != "SELL":
                    if signal == "HOLD":
                        signal = "BUY"
                    confidence += 0.1
                    reasons.append(f"Price above MA20")
                elif current_price < ma_20 and signal != "BUY":
                    if signal == "HOLD":
                        signal = "SELL"
                    confidence += 0.1
                    reasons.append(f"Price below MA20")
            
            # Get AH premium if applicable
            ah_premium = self.get_ah_premium(symbol)
            if ah_premium:
                premium_rate = ah_premium.get("premium_rate", 0)
                if premium_rate > 10:
                    reasons.append(f"AH premium: {premium_rate:.1f}% (A股贵)")
                elif premium_rate < -10:
                    reasons.append(f"AH discount: {premium_rate:.1f}% (H股贵)")
            
            # Get HK Connect flow
            flow = self.get_hk_connect_flow(days=5)
            if flow:
                total_inflow = flow.get("total_inflow", 0)
                if total_inflow > 0:
                    reasons.append(f"南下资金净流入: {total_inflow:.1f}亿")
                elif total_inflow < 0:
                    reasons.append(f"南下资金净流出: {abs(total_inflow):.1f}亿")
            
            # Cap confidence
            confidence = min(confidence, 1.0)
            
            result = {
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "reasons": reasons,
                "indicators": indicators,
            }
            
            logger.info(
                f"Trading signal for {symbol}: {signal} "
                f"(confidence: {confidence:.2f}, reasons: {', '.join(reasons)})"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to generate trading signal for {symbol}: {e}")
            return {
                "symbol": symbol,
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}",
            }


# Singleton instance
_hk_stock_provider: Optional[HKStockMarketDataProvider] = None


def get_hk_stock_market_data_provider() -> HKStockMarketDataProvider:
    """Get singleton instance of HK stock market data provider."""
    global _hk_stock_provider
    if _hk_stock_provider is None:
        _hk_stock_provider = HKStockMarketDataProvider()
    return _hk_stock_provider

