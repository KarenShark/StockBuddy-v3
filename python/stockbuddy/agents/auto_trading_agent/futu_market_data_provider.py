"""
富途市场数据提供器
使用富途OpenAPI获取真实市场数据
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

try:
    from futu import OpenQuoteContext, RET_OK, KLType, SubType
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    logger.warning("futu-api not installed")


class FutuMarketDataProvider:
    """
    富途市场数据提供器
    
    提供真实的港股市场数据：
    - 实时行情
    - 历史K线
    - 技术指标计算
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11111):
        """
        初始化富途数据提供器
        
        Args:
            host: FutuOpenD地址
            port: FutuOpenD端口
        """
        if not FUTU_AVAILABLE:
            raise ImportError("futu-api not installed. Run: uv pip install futu-api")
        
        self.host = host
        self.port = port
        self.quote_ctx: Optional[OpenQuoteContext] = None
        self._connected = False
        
        logger.info(f"FutuMarketDataProvider initialized: {host}:{port}")
    
    async def connect(self) -> bool:
        """连接到FutuOpenD"""
        try:
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            
            # 测试连接
            ret, data = self.quote_ctx.get_global_state()
            if ret != RET_OK:
                logger.error(f"Failed to connect: {data}")
                return False
            
            self._connected = True
            logger.info("✅ Connected to FutuOpenD for market data")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def _format_symbol(self, symbol: str) -> str:
        """格式化股票代码"""
        if '.' in symbol:
            return symbol
        return f"HK.{symbol}"
    
    async def get_real_time_price(self, symbol: str) -> Optional[float]:
        """
        获取实时价格
        
        Args:
            symbol: 股票代码 (如: 00700)
            
        Returns:
            当前价格或None
        """
        if not self._connected:
            await self.connect()
        
        try:
            futu_symbol = self._format_symbol(symbol)
            
            ret, data = self.quote_ctx.get_market_snapshot([futu_symbol])
            if ret != RET_OK:
                logger.error(f"Failed to get price for {symbol}: {data}")
                return None
            
            if not data.empty:
                price = float(data.iloc[0]['last_price'])
                if price > 0:
                    return price
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    async def get_historical_klines(
        self,
        symbol: str,
        period: str = '1d',
        count: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        获取历史K线数据
        
        Args:
            symbol: 股票代码
            period: 周期 (1m, 5m, 15m, 30m, 60m, 1d, 1w, 1M)
            count: 数量
            
        Returns:
            DataFrame with columns: time, open, high, low, close, volume
        """
        if not self._connected:
            await self.connect()
        
        try:
            futu_symbol = self._format_symbol(symbol)
            
            # 转换周期
            ktype_map = {
                '1m': KLType.K_1M,
                '5m': KLType.K_5M,
                '15m': KLType.K_15M,
                '30m': KLType.K_30M,
                '60m': KLType.K_60M,
                '1d': KLType.K_DAY,
                '1w': KLType.K_WEEK,
                '1M': KLType.K_MON,
            }
            ktype = ktype_map.get(period, KLType.K_DAY)
            
            ret, data = self.quote_ctx.get_cur_kline(
                code=futu_symbol,
                num=count,
                ktype=ktype,
            )
            
            if ret != RET_OK:
                logger.error(f"Failed to get klines for {symbol}: {data}")
                return None
            
            if not data.empty:
                # 重命名列以匹配标准格式
                df = data.rename(columns={
                    'time_key': 'time',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                })
                
                return df[['time', 'open', 'high', 'low', 'close', 'volume']]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return None
    
    async def calculate_technical_indicators(
        self,
        symbol: str,
        period: str = '1d',
        count: int = 100,
    ) -> Optional[Dict[str, any]]:
        """
        计算技术指标
        
        Returns:
            dict with: sma_20, sma_50, rsi, macd, signal, histogram, bb_upper, bb_middle, bb_lower
        """
        df = await self.get_historical_klines(symbol, period, count)
        if df is None or df.empty:
            return None
        
        try:
            close = df['close'].values
            
            # SMA
            sma_20 = self._calculate_sma(close, 20)
            sma_50 = self._calculate_sma(close, 50)
            
            # RSI
            rsi = self._calculate_rsi(close, 14)
            
            # MACD
            macd, signal, histogram = self._calculate_macd(close)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close, 20, 2)
            
            return {
                'current_price': float(close[-1]),
                'sma_20': float(sma_20[-1]) if sma_20 is not None else None,
                'sma_50': float(sma_50[-1]) if sma_50 is not None else None,
                'rsi': float(rsi[-1]) if rsi is not None else None,
                'macd': float(macd[-1]) if macd is not None else None,
                'macd_signal': float(signal[-1]) if signal is not None else None,
                'macd_histogram': float(histogram[-1]) if histogram is not None else None,
                'bb_upper': float(bb_upper[-1]) if bb_upper is not None else None,
                'bb_middle': float(bb_middle[-1]) if bb_middle is not None else None,
                'bb_lower': float(bb_lower[-1]) if bb_lower is not None else None,
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return None
    
    def _calculate_sma(self, data: np.ndarray, period: int) -> Optional[np.ndarray]:
        """计算简单移动平均"""
        if len(data) < period:
            return None
        return pd.Series(data).rolling(window=period).mean().values
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> Optional[np.ndarray]:
        """计算RSI"""
        if len(data) < period + 1:
            return None
        
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = pd.Series(gains).rolling(window=period).mean().values
        avg_loss = pd.Series(losses).rolling(window=period).mean().values
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return np.concatenate([np.array([np.nan]), rsi])
    
    def _calculate_macd(
        self,
        data: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
    ) -> tuple:
        """计算MACD"""
        if len(data) < slow:
            return None, None, None
        
        ema_fast = pd.Series(data).ewm(span=fast).mean().values
        ema_slow = pd.Series(data).ewm(span=slow).mean().values
        
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=signal_period).mean().values
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(
        self,
        data: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple:
        """计算布林带"""
        if len(data) < period:
            return None, None, None
        
        sma = pd.Series(data).rolling(window=period).mean().values
        std = pd.Series(data).rolling(window=period).std().values
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return upper, sma, lower
    
    async def get_trading_signal(self, symbol: str) -> Optional[Dict[str, any]]:
        """
        生成交易信号
        
        Returns:
            dict with: signal ('BUY', 'SELL', 'HOLD'), strength (0-100), reasons
        """
        indicators = await self.calculate_technical_indicators(symbol)
        if not indicators:
            return None
        
        signals = []
        reasons = []
        
        # RSI信号
        rsi = indicators.get('rsi')
        if rsi:
            if rsi < 30:
                signals.append(1)  # 买入
                reasons.append(f"RSI超卖 ({rsi:.1f})")
            elif rsi > 70:
                signals.append(-1)  # 卖出
                reasons.append(f"RSI超买 ({rsi:.1f})")
            else:
                signals.append(0)
        
        # MACD信号
        macd = indicators.get('macd')
        signal = indicators.get('macd_signal')
        if macd and signal:
            if macd > signal:
                signals.append(1)
                reasons.append("MACD金叉")
            else:
                signals.append(-1)
                reasons.append("MACD死叉")
        
        # 布林带信号
        price = indicators.get('current_price')
        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        if price and bb_upper and bb_lower:
            if price < bb_lower:
                signals.append(1)
                reasons.append("价格触及布林带下轨")
            elif price > bb_upper:
                signals.append(-1)
                reasons.append("价格触及布林带上轨")
        
        # SMA趋势
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        if price and sma_20 and sma_50:
            if price > sma_20 > sma_50:
                signals.append(1)
                reasons.append("价格位于均线之上")
            elif price < sma_20 < sma_50:
                signals.append(-1)
                reasons.append("价格位于均线之下")
        
        # 综合信号
        if not signals:
            return {
                'signal': 'HOLD',
                'strength': 50,
                'reasons': ['无明确信号'],
                'indicators': indicators,
            }
        
        avg_signal = sum(signals) / len(signals)
        
        if avg_signal > 0.3:
            signal_type = 'BUY'
            strength = min(100, int(50 + avg_signal * 50))
        elif avg_signal < -0.3:
            signal_type = 'SELL'
            strength = min(100, int(50 - avg_signal * 50))
        else:
            signal_type = 'HOLD'
            strength = 50
        
        return {
            'signal': signal_type,
            'strength': strength,
            'reasons': reasons,
            'indicators': indicators,
        }
    
    def __del__(self):
        """确保连接被关闭"""
        if self._connected and self.quote_ctx:
            try:
                self.quote_ctx.close()
            except:
                pass

