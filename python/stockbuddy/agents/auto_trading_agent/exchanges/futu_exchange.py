"""
富途证券Exchange适配器
支持实盘和模拟盘交易
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from futu import (
        OpenQuoteContext,
        OpenSecTradeContext,
        RET_OK,
        TrdEnv,
        TrdSide,
        OrderType,
        TrdMarket,
        ModifyOrderOp,
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    logger.warning("futu-api not installed. Run: uv pip install futu-api")

from .base_exchange import ExchangeBase, ExchangeType


class FutuExchange(ExchangeBase):
    """
    富途证券Exchange适配器
    
    使用前需要：
    1. 下载并安装 FutuOpenD: https://www.futunn.com/download/openAPI
    2. 启动 FutuOpenD 客户端
    3. 在富途牛牛App中开通模拟账户
    """
    
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 11111,
        env: str = 'SIMULATE',  # SIMULATE 或 REAL
        market: str = 'HK',  # HK, US, CN, HKCC
        initial_capital: float = 1000000.0,
    ):
        """
        初始化富途Exchange
        
        Args:
            host: FutuOpenD服务器地址
            port: FutuOpenD端口号
            env: 交易环境 SIMULATE(模拟) 或 REAL(实盘)
            market: 交易市场 HK(港股) US(美股) CN(A股)
            initial_capital: 初始资金（仅用于模拟盘）
        """
        if not FUTU_AVAILABLE:
            raise ImportError("futu-api not installed. Run: uv pip install futu-api")
        
        self.host = host
        self.port = port
        self.env = TrdEnv.SIMULATE if env == 'SIMULATE' else TrdEnv.REAL
        self.market_str = market
        self.initial_capital = initial_capital
        
        # 设置市场类型
        market_map = {
            'HK': TrdMarket.HK,
            'US': TrdMarket.US,
            'CN': TrdMarket.CN,
            'HKCC': TrdMarket.HKCC,
        }
        self.market = market_map.get(market, TrdMarket.HK)
        
        # 初始化连接
        self.quote_ctx: Optional[OpenQuoteContext] = None
        self.trade_ctx: Optional[OpenSecTradeContext] = None
        
        # 内部状态
        self._connected = False
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._trades: List[Dict[str, Any]] = []
        
        logger.info(f"FutuExchange initialized: {host}:{port}, env={env}, market={market}")
    
    async def connect(self) -> bool:
        """连接到FutuOpenD"""
        try:
            # 创建行情连接
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            
            # 创建交易连接
            self.trade_ctx = OpenSecTradeContext(
                filter_trdmarket=self.market,
                host=self.host,
                port=self.port,
                security_firm=0  # 富途证券
            )
            
            # 测试连接
            ret, data = self.quote_ctx.get_global_state()
            if ret != RET_OK:
                logger.error(f"Failed to connect to FutuOpenD: {data}")
                return False
            
            self._connected = True
            logger.info(f"✅ Connected to FutuOpenD: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to FutuOpenD: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        try:
            if self.quote_ctx:
                self.quote_ctx.close()
            if self.trade_ctx:
                self.trade_ctx.close()
            self._connected = False
            logger.info("Disconnected from FutuOpenD")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def _format_symbol(self, symbol: str) -> str:
        """
        格式化股票代码为富途格式
        00700 -> HK.00700
        """
        if '.' in symbol:
            return symbol
        
        market_prefix = self.market_str
        return f"{market_prefix}.{symbol}"
    
    def _unformat_symbol(self, futu_symbol: str) -> str:
        """
        将富途格式转换为标准格式
        HK.00700 -> 00700
        """
        if '.' in futu_symbol:
            return futu_symbol.split('.')[1]
        return futu_symbol
    
    async def get_balance(self) -> Dict[str, float]:
        """获取账户余额"""
        if not self._connected:
            await self.connect()
        
        try:
            # 获取账户资金
            ret, data = self.trade_ctx.accinfo_query(trd_env=self.env)
            if ret != RET_OK:
                logger.error(f"Failed to query account info: {data}")
                return {
                    'cash': self.initial_capital,
                    'total': self.initial_capital,
                }
            
            # 解析数据
            if not data.empty:
                row = data.iloc[0]
                return {
                    'cash': float(row.get('cash', 0)),
                    'market_value': float(row.get('market_val', 0)),
                    'total': float(row.get('total_assets', 0)),
                    'frozen_cash': float(row.get('frozen_cash', 0)),
                }
            
            return {
                'cash': self.initial_capital,
                'total': self.initial_capital,
            }
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {
                'cash': self.initial_capital,
                'total': self.initial_capital,
            }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓"""
        if not self._connected:
            await self.connect()
        
        try:
            ret, data = self.trade_ctx.position_list_query(trd_env=self.env)
            if ret != RET_OK:
                logger.warning(f"Failed to query positions: {data}")
                return []
            
            positions = []
            if not data.empty:
                for _, row in data.iterrows():
                    positions.append({
                        'symbol': self._unformat_symbol(row['code']),
                        'quantity': int(row['qty']),
                        'available': int(row.get('can_sell_qty', 0)),
                        'cost_price': float(row.get('cost_price', 0)),
                        'market_price': float(row.get('market_val', 0)) / int(row['qty']) if int(row['qty']) > 0 else 0,
                        'market_value': float(row.get('market_val', 0)),
                        'pnl': float(row.get('pl_val', 0)),
                        'pnl_ratio': float(row.get('pl_ratio', 0)),
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = 'MARKET',
    ) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 股票代码 (如: 00700)
            side: BUY 或 SELL
            quantity: 数量（股）
            price: 价格（限价单必填）
            order_type: MARKET(市价) 或 LIMIT(限价)
        """
        if not self._connected:
            await self.connect()
        
        try:
            futu_symbol = self._format_symbol(symbol)
            
            # 转换方向
            futu_side = TrdSide.BUY if side.upper() == 'BUY' else TrdSide.SELL
            
            # 转换订单类型
            futu_order_type = OrderType.MARKET if order_type == 'MARKET' else OrderType.NORMAL
            
            # 下单
            if order_type == 'MARKET':
                ret, data = self.trade_ctx.place_order(
                    price=0,  # 市价单价格填0
                    qty=quantity,
                    code=futu_symbol,
                    trd_side=futu_side,
                    order_type=futu_order_type,
                    trd_env=self.env,
                )
            else:
                if price is None:
                    raise ValueError("Limit order requires price")
                ret, data = self.trade_ctx.place_order(
                    price=price,
                    qty=quantity,
                    code=futu_symbol,
                    trd_side=futu_side,
                    order_type=futu_order_type,
                    trd_env=self.env,
                )
            
            if ret != RET_OK:
                logger.error(f"Failed to place order: {data}")
                return {
                    'success': False,
                    'error': str(data),
                }
            
            # 解析订单结果
            if not data.empty:
                row = data.iloc[0]
                order_id = row.get('order_id', '')
                
                logger.info(f"✅ Order placed: {side} {quantity} {symbol} @ {price or 'MARKET'}, order_id={order_id}")
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'order_type': order_type,
                    'timestamp': datetime.now().isoformat(),
                }
            
            return {
                'success': False,
                'error': 'No order data returned',
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        if not self._connected:
            await self.connect()
        
        try:
            ret, data = self.trade_ctx.modify_order(
                modify_order_op=ModifyOrderOp.CANCEL,
                order_id=order_id,
                qty=0,
                price=0,
                trd_env=self.env,
            )
            
            if ret != RET_OK:
                logger.error(f"Failed to cancel order: {data}")
                return False
            
            logger.info(f"✅ Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """查询订单状态"""
        if not self._connected:
            await self.connect()
        
        try:
            ret, data = self.trade_ctx.order_list_query(trd_env=self.env)
            if ret != RET_OK:
                logger.error(f"Failed to query orders: {data}")
                return None
            
            if not data.empty:
                order = data[data['order_id'] == order_id]
                if not order.empty:
                    row = order.iloc[0]
                    return {
                        'order_id': order_id,
                        'status': row.get('order_status', ''),
                        'filled_qty': int(row.get('dealt_qty', 0)),
                        'avg_price': float(row.get('dealt_avg_price', 0)),
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """获取实时市价"""
        if not self._connected:
            await self.connect()
        
        try:
            futu_symbol = self._format_symbol(symbol)
            
            ret, data = self.quote_ctx.get_market_snapshot([futu_symbol])
            if ret != RET_OK:
                logger.error(f"Failed to get market price for {symbol}: {data}")
                return None
            
            if not data.empty:
                row = data.iloc[0]
                price = float(row.get('last_price', 0))
                if price > 0:
                    return price
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market price: {e}")
            return None
    
    async def get_kline(
        self,
        symbol: str,
        period: str = '1d',
        count: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码
            period: 周期 (1m, 5m, 15m, 30m, 60m, 1d, 1w, 1M)
            count: 数量
        """
        if not self._connected:
            await self.connect()
        
        try:
            from futu import KLType
            
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
                logger.error(f"Failed to get kline for {symbol}: {data}")
                return None
            
            if not data.empty:
                klines = []
                for _, row in data.iterrows():
                    klines.append({
                        'time': row['time_key'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume']),
                    })
                return klines
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting kline: {e}")
            return None
    
    def __del__(self):
        """析构函数：确保连接被关闭"""
        if self._connected:
            try:
                if self.quote_ctx:
                    self.quote_ctx.close()
                if self.trade_ctx:
                    self.trade_ctx.close()
            except:
                pass

