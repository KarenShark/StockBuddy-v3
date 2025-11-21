"""Hong Kong Stock Paper Trading (模拟交易) Exchange Adapter

This adapter provides simulated trading for Hong Kong stocks with realistic:
- Trading hours and auction periods
- Lot sizes (trading units)
- HK market fees (stamp duty, trading levy, settlement fee)
- HKD pricing
- Market data integration via AdapterManager
- Slippage simulation (realistic price impact)
- Order latency (network and processing delays)
- Market impact (large order price movement)
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from stockbuddy.adapters.assets.manager import get_adapter_manager

from .base_exchange import ExchangeBase, ExchangeType, Order, OrderStatus

logger = logging.getLogger(__name__)


# Hong Kong Stock Lot Size Mapping (常见股票的每手股数)
# Default is 100 shares per lot, but some stocks have different lot sizes
HK_STOCK_LOT_SIZES = {
    "00700": 100,  # 腾讯控股
    "09988": 50,   # 阿里巴巴-SW
    "00941": 200,  # 中国移动
    "02318": 400,  # 中国平安
    "01299": 500,  # 友邦保险
    "00939": 500,  # 建设银行
    "01398": 1000, # 工商银行
    "00388": 1000, # 香港交易所
    "03690": 200,  # 美团-W
    "01810": 200,  # 小米集团-W
    # Add more as needed
}

DEFAULT_LOT_SIZE = 100  # Most HK stocks trade in 100-share lots


class HKStockPaperTrading(ExchangeBase):
    """
    Simulated trading for Hong Kong stocks with realistic market characteristics.
    
    Features:
    - HK trading hours (09:30-12:00, 13:00-16:00 HKT)
    - Auction periods (09:00-09:30 open, 16:00-16:10 close)
    - Lot-based trading (最小交易单位)
    - Market fees (stamp duty 0.13%, trading levy, settlement fee)
    - Real-time price data via AdapterManager
    - HKD currency
    - Slippage simulation for realistic execution
    - Order latency simulation
    - Market impact for large orders
    """

    def __init__(
        self,
        initial_balance: float = 1000000.0,
        enable_slippage: bool = True,
        enable_latency: bool = True,
        enable_market_impact: bool = True,
    ):
        """
        Initialize HK stock paper trading.
        
        Args:
            initial_balance: Starting capital in HKD (default: 1,000,000 HKD)
            enable_slippage: Enable slippage simulation (default: True)
            enable_latency: Enable order latency simulation (default: True)
            enable_market_impact: Enable market impact simulation (default: True)
        """
        super().__init__(ExchangeType.PAPER)
        self.initial_balance = initial_balance
        self.balance = initial_balance  # Available cash in HKD
        self.positions: Dict[str, Dict[str, Any]] = {}  # {symbol: position_data}
        self.is_connected = True
        
        # Portfolio value history tracking
        self.portfolio_history: List[Dict[str, Any]] = []
        self._record_portfolio_snapshot()  # Record initial state
        
        # Fee structure (Hong Kong Stock Exchange)
        self.stamp_duty_rate = 0.0013  # 印花税 0.13%
        self.trading_fee_rate = 0.00005  # 交易费 0.005%
        self.settlement_fee_rate = 0.00002  # 结算费 0.002%
        self.transaction_levy_rate = 0.000027  # 交易征费 0.0027%
        
        # Realism simulation settings
        self.enable_slippage = enable_slippage
        self.enable_latency = enable_latency
        self.enable_market_impact = enable_market_impact
        
        # Slippage configuration (滑点配置)
        # Typical HK stock slippage: 0.03% - 0.10%
        self.slippage_bps_min = 3  # 最小滑点: 3个基点 = 0.03%
        self.slippage_bps_max = 10  # 最大滑点: 10个基点 = 0.10%
        
        # Order latency configuration (订单延迟配置)
        # Typical latency: API (50-200ms) + Broker (10-100ms) + Exchange (10-50ms)
        self.latency_ms_min = 70   # 最小延迟: 70ms
        self.latency_ms_max = 350  # 最大延迟: 350ms
        
        # Market impact configuration (市场冲击配置)
        # Large orders impact price more
        self.market_impact_threshold_lots = 500  # 超过500手开始有明显市场冲击
        self.market_impact_bps_per_1000_lots = 5  # 每1000手额外0.05%冲击
        
        # Get adapter manager for market data
        self.adapter_manager = get_adapter_manager()
        
        logger.info(f"HK Stock Paper Trading initialized with balance: ${initial_balance:,.2f} HKD")
        logger.info(
            f"Realism settings: slippage={enable_slippage}, "
            f"latency={enable_latency}, market_impact={enable_market_impact}"
        )

    # ============ Connection Management ============

    async def connect(self) -> bool:
        """Paper trading is always connected"""
        self.is_connected = True
        logger.info("HK Stock Paper Trading connected (simulated)")
        return True

    async def disconnect(self) -> bool:
        """Disconnect paper trading"""
        self.is_connected = False
        logger.info("HK Stock Paper Trading disconnected")
        return True

    async def validate_connection(self) -> bool:
        """Paper trading is always valid"""
        return self.is_connected

    # ============ Market Hours & Trading Rules ============

    def is_market_open(self) -> bool:
        """
        Check if HK stock market is currently open for trading.
        
        Trading hours (HKT):
        - Morning: 09:30 - 12:00
        - Afternoon: 13:00 - 16:00
        
        Returns:
            True if market is open
        """
        now = datetime.now()
        current_time = now.time()
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Morning session: 09:30 - 12:00
        morning_start = time(9, 30)
        morning_end = time(12, 0)
        
        # Afternoon session: 13:00 - 16:00
        afternoon_start = time(13, 0)
        afternoon_end = time(16, 0)
        
        is_morning_session = morning_start <= current_time < morning_end
        is_afternoon_session = afternoon_start <= current_time <= afternoon_end
        
        return is_morning_session or is_afternoon_session

    def is_in_auction(self) -> bool:
        """
        Check if currently in auction period.
        
        Auction periods (HKT):
        - Pre-opening auction: 09:00 - 09:30
        - Closing auction: 16:00 - 16:10
        
        Returns:
            True if in auction period
        """
        now = datetime.now()
        current_time = now.time()
        
        if now.weekday() >= 5:
            return False
        
        # Pre-opening auction
        pre_open_start = time(9, 0)
        pre_open_end = time(9, 30)
        
        # Closing auction
        close_auction_start = time(16, 0)
        close_auction_end = time(16, 10)
        
        is_pre_open = pre_open_start <= current_time < pre_open_end
        is_closing = close_auction_start <= current_time < close_auction_end
        
        return is_pre_open or is_closing

    def get_lot_size(self, symbol: str) -> int:
        """
        Get the lot size (trading unit) for a stock.
        
        Args:
            symbol: Stock symbol (e.g., "HKEX:00700" or "00700")
        
        Returns:
            Number of shares per lot
        """
        # Extract symbol code (remove HKEX: prefix if present)
        if ":" in symbol:
            _, code = symbol.split(":", 1)
        else:
            code = symbol
        
        # Pad to 5 digits
        code = code.zfill(5)
        
        return HK_STOCK_LOT_SIZES.get(code, DEFAULT_LOT_SIZE)

    def calculate_fees(self, notional: float, side: str) -> float:
        """
        Calculate total trading fees for HK stocks.
        
        Fees include:
        - Stamp duty: 0.13% (on buy and sell)
        - Trading fee: 0.005%
        - Settlement fee: 0.002%
        - Transaction levy: 0.0027%
        
        Args:
            notional: Transaction amount in HKD
            side: "buy" or "sell"
        
        Returns:
            Total fees in HKD
        """
        stamp_duty = notional * self.stamp_duty_rate
        trading_fee = notional * self.trading_fee_rate
        settlement_fee = notional * self.settlement_fee_rate
        transaction_levy = notional * self.transaction_levy_rate
        
        total_fees = stamp_duty + trading_fee + settlement_fee + transaction_levy
        
        logger.debug(
            f"Fees for {side} ${notional:,.2f} HKD: "
            f"stamp_duty=${stamp_duty:.2f}, "
            f"trading_fee=${trading_fee:.2f}, "
            f"settlement_fee=${settlement_fee:.2f}, "
            f"transaction_levy=${transaction_levy:.2f}, "
            f"total=${total_fees:.2f}"
        )
        
        return total_fees

    # ============ Account Information ============

    async def get_balance(self) -> Dict[str, float]:
        """
        Get simulated account balances.
        
        Returns:
            Dictionary with HKD and stock positions
        """
        balances = {"HKD": self.balance}
        
        # Add positions as assets
        for symbol, pos_data in self.positions.items():
            balances[symbol] = pos_data["quantity"]
        
        return balances

    async def get_asset_balance(self, asset: str) -> float:
        """
        Get balance for a specific asset.
        
        Args:
            asset: Asset symbol or "HKD"
        
        Returns:
            Available balance
        """
        if asset == "HKD":
            return self.balance
        
        # Check if we have a position
        if asset in self.positions:
            return self.positions[asset]["quantity"]
        
        return 0.0

    # ============ Market Data ============

    async def get_current_price(self, symbol: str) -> float:
        """
        Get current real-time price for a HK stock.
        
        Args:
            symbol: Stock symbol in internal format (e.g., "HKEX:00700")
        
        Returns:
            Current price in HKD
        """
        try:
            # Ensure symbol has HKEX: prefix
            if not symbol.startswith("HKEX:"):
                symbol = f"HKEX:{symbol}"
            
            # Get price from adapter manager
            price_data = self.adapter_manager.get_real_time_price(symbol)
            
            if price_data and price_data.price:
                logger.debug(f"Got price for {symbol}: ${price_data.price:.2f} HKD")
                return float(price_data.price)
            else:
                logger.warning(f"No price data available for {symbol}")
                return 0.0
        
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return 0.0

    async def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker data.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Ticker data dictionary
        """
        try:
            # Ensure symbol has HKEX: prefix
            if not symbol.startswith("HKEX:"):
                symbol = f"HKEX:{symbol}"
            
            # Get current price
            current_price = await self.get_current_price(symbol)
            
            # For paper trading, we simplify ticker data
            # In production, you'd fetch historical data for 24h high/low/volume
            return {
                "symbol": symbol,
                "current_price": current_price,
                "currency": "HKD",
            }
        
        except Exception as e:
            logger.error(f"Failed to get 24h ticker for {symbol}: {e}")
            return {}

    # ============ Order Management ============

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_type: str = "limit",
        **kwargs,
    ) -> Order:
        """
        Place a simulated order for HK stocks.
        
        Important: quantity should be in LOTS, not shares!
        The order will be placed for (quantity * lot_size) shares.
        
        Args:
            symbol: Stock symbol (e.g., "HKEX:00700")
            side: "buy" or "sell"
            quantity: Number of LOTS to trade
            price: Order price per share (None for market)
            order_type: "limit" or "market"
            **kwargs: Additional parameters
        
        Returns:
            Order object
        """
        order_id = str(uuid.uuid4())[:8]
        
        # Ensure symbol has HKEX: prefix
        if not symbol.startswith("HKEX:"):
            symbol = f"HKEX:{symbol}"
        
        # Get lot size
        lot_size = self.get_lot_size(symbol)
        
        # Convert lots to shares
        shares = int(quantity * lot_size)
        
        # Get current price if market order
        if price is None or order_type == "market":
            price = await self.get_current_price(symbol)
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side.lower(),
            quantity=shares,  # Store in shares
            price=price,
            order_type=order_type,
            trade_type=kwargs.get("trade_type"),
        )
        
        # Check market hours (for simulation, we allow trading anytime in paper mode)
        # In production, you might want to enforce trading hours
        
        # Immediately fill market orders
        if order_type == "market":
            await self._fill_order(order)
        
        self.orders[order_id] = order
        logger.info(
            f"HK Stock Order placed: {order_id} - {side} {quantity} lots "
            f"({shares} shares) of {symbol} @ ${price:.2f} HKD"
        )
        
        return order

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"HK Stock Order cancelled: {order_id}")
            return True
        return False

    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """Get order status."""
        if order_id in self.orders:
            return self.orders[order_id].status
        return OrderStatus.EXPIRED

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders."""
        open_orders = [
            o
            for o in self.orders.values()
            if o.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
        ]
        if symbol:
            open_orders = [o for o in open_orders if o.symbol == symbol]
        return open_orders

    async def get_order_history(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Order]:
        """Get order history."""
        history = self.order_history
        if symbol:
            history = [o for o in history if o.symbol == symbol]
        return history[-limit:]

    # ============ Position Management ============

    async def get_open_positions(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get open positions."""
        logger.info(f"📊 Getting open positions - Total: {len(self.positions)}")
        for sym, pos in self.positions.items():
            logger.info(f"   - {sym}: {pos['quantity']} shares @ ${pos.get('entry_price', 0):.2f}")
        
        if symbol:
            if symbol in self.positions:
                return {symbol: self.positions[symbol]}
            return {}
        return self.positions.copy()

    async def get_position_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific position."""
        return self.positions.get(symbol)

    # ============ Trade Execution ============

    async def execute_buy(
        self,
        symbol: str,
        quantity: float,  # in LOTS
        price: Optional[float] = None,
        **kwargs,
    ) -> Optional[Order]:
        """
        Execute a buy order for HK stocks.
        
        Args:
            symbol: Stock symbol
            quantity: Number of LOTS to buy
            price: Price per share (None for market)
            **kwargs: Additional parameters
        
        Returns:
            Order or None if failed
        """
        # Ensure symbol has HKEX: prefix
        if not symbol.startswith("HKEX:"):
            symbol = f"HKEX:{symbol}"
        
        # Get lot size
        lot_size = self.get_lot_size(symbol)
        shares = int(quantity * lot_size)
        
        # Get price
        if price is None:
            price = await self.get_current_price(symbol)
        
        if price <= 0:
            logger.warning(f"Invalid price for {symbol}: ${price}")
            return None
        
        # Calculate costs
        notional = shares * price
        fees = self.calculate_fees(notional, "buy")
        total_cost = notional + fees
        
        # Check balance
        if total_cost > self.balance:
            logger.warning(
                f"Insufficient balance for buy: need ${total_cost:,.2f} HKD, "
                f"have ${self.balance:,.2f} HKD"
            )
            return None
        
        # Place and fill order
        order = await self.place_order(symbol, "buy", quantity, price, "market")
        
        return order

    async def execute_sell(
        self,
        symbol: str,
        quantity: float,  # in LOTS
        price: Optional[float] = None,
        **kwargs,
    ) -> Optional[Order]:
        """
        Execute a sell order for HK stocks.
        
        Args:
            symbol: Stock symbol
            quantity: Number of LOTS to sell
            price: Price per share (None for market)
            **kwargs: Additional parameters
        
        Returns:
            Order or None if failed
        """
        # Ensure symbol has HKEX: prefix
        if not symbol.startswith("HKEX:"):
            symbol = f"HKEX:{symbol}"
        
        # Check if we have the position
        if symbol not in self.positions:
            logger.warning(f"No position to sell for {symbol}")
            return None
        
        # Get lot size
        lot_size = self.get_lot_size(symbol)
        shares = int(quantity * lot_size)
        
        # Check position size
        if self.positions[symbol]["quantity"] < shares:
            logger.warning(
                f"Insufficient position: have {self.positions[symbol]['quantity']} shares, "
                f"trying to sell {shares} shares"
            )
            return None
        
        # Get price
        if price is None:
            price = await self.get_current_price(symbol)
        
        if price <= 0:
            logger.warning(f"Invalid price for {symbol}: ${price}")
            return None
        
        # Place and fill order
        order = await self.place_order(symbol, "sell", quantity, price, "market")
        
        return order

    # ============ Utilities ============

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to HK stock format.
        
        Args:
            symbol: Original symbol (e.g., "00700", "HKEX:00700")
        
        Returns:
            Normalized symbol with HKEX: prefix
        """
        if symbol.startswith("HKEX:"):
            return symbol
        
        # Pad to 5 digits and add prefix
        code = symbol.zfill(5)
        return f"HKEX:{code}"

    async def get_fee_tier(self) -> Dict[str, float]:
        """
        Get HK market fee rates.
        
        Returns:
            Fee dictionary
        """
        return {
            "stamp_duty": self.stamp_duty_rate,
            "trading_fee": self.trading_fee_rate,
            "settlement_fee": self.settlement_fee_rate,
            "transaction_levy": self.transaction_levy_rate,
        }

    async def get_trading_limits(self, symbol: str) -> Dict[str, Any]:
        """
        Get trading limits for a HK stock.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Limits dictionary
        """
        lot_size = self.get_lot_size(symbol)
        
        return {
            "min_quantity": 1,  # 1 lot minimum
            "lot_size": lot_size,
            "quantity_precision": 0,  # Whole lots only
            "price_precision": 3,  # HK stocks trade in 0.001 increments
        }

    # ============ Private Methods ============

    def _calculate_slippage(self, price: float, side: str) -> float:
        """
        Calculate slippage for an order.
        
        Slippage simulates the difference between expected and actual execution price
        due to market movement and bid-ask spread.
        
        Args:
            price: Base price
            side: "buy" or "sell"
        
        Returns:
            Adjusted price with slippage
        """
        if not self.enable_slippage:
            return price
        
        # Random slippage between min and max
        slippage_bps = random.uniform(self.slippage_bps_min, self.slippage_bps_max)
        slippage_factor = slippage_bps / 10000  # Convert basis points to decimal
        
        if side == "buy":
            # Buying: pay more (unfavorable slippage)
            adjusted_price = price * (1 + slippage_factor)
        else:
            # Selling: receive less (unfavorable slippage)
            adjusted_price = price * (1 - slippage_factor)
        
        logger.debug(
            f"Slippage: {side} {price:.3f} → {adjusted_price:.3f} "
            f"({slippage_bps:.1f} bps, {slippage_factor*100:.3f}%)"
        )
        
        return adjusted_price
    
    def _calculate_market_impact(self, symbol: str, quantity: int, price: float, side: str) -> float:
        """
        Calculate market impact for large orders.
        
        Large orders move the market price unfavorably:
        - Large buys push the price up
        - Large sells push the price down
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Base price
            side: "buy" or "sell"
        
        Returns:
            Adjusted price with market impact
        """
        if not self.enable_market_impact:
            return price
        
        # Convert shares to lots
        lot_size = self.get_lot_size(symbol)
        lots = quantity / lot_size
        
        # Only apply market impact for orders above threshold
        if lots <= self.market_impact_threshold_lots:
            return price
        
        # Calculate impact based on order size
        excess_lots = lots - self.market_impact_threshold_lots
        impact_factor = (excess_lots / 1000) * (self.market_impact_bps_per_1000_lots / 10000)
        
        # Cap maximum impact at 1% (100 bps)
        impact_factor = min(impact_factor, 0.01)
        
        if side == "buy":
            # Large buy orders push price up
            adjusted_price = price * (1 + impact_factor)
        else:
            # Large sell orders push price down
            adjusted_price = price * (1 - impact_factor)
        
        if impact_factor > 0:
            logger.info(
                f"Market impact: {side} {lots:.0f} lots - "
                f"{price:.3f} → {adjusted_price:.3f} "
                f"({impact_factor*10000:.1f} bps, {impact_factor*100:.3f}%)"
            )
        
        return adjusted_price
    
    async def _simulate_order_latency(self, symbol: str) -> Optional[float]:
        """
        Simulate order latency (network + processing + exchange delays).
        
        During this delay, the market price may have moved.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            New price after latency (or None if unavailable)
        """
        if not self.enable_latency:
            return None
        
        # Random latency between min and max
        latency_ms = random.uniform(self.latency_ms_min, self.latency_ms_max)
        latency_seconds = latency_ms / 1000
        
        logger.debug(f"Simulating order latency: {latency_ms:.0f}ms")
        
        # Sleep to simulate delay
        await asyncio.sleep(latency_seconds)
        
        # Fetch new price after delay (price might have changed)
        try:
            new_price = await self.get_current_price(symbol)
            if new_price and new_price > 0:
                logger.debug(f"Price after latency: ${new_price:.3f} HKD")
                return new_price
        except Exception as e:
            logger.warning(f"Failed to get price after latency: {e}")
        
        return None

    async def _fill_order(self, order: Order) -> bool:
        """
        Fill an order (update balance, positions, account for fees).
        
        Simulates realistic execution with:
        - Order latency (price may change during delay)
        - Slippage (bid-ask spread and market movement)
        - Market impact (large orders move prices)
        
        Args:
            order: Order to fill
        
        Returns:
            True if filled successfully
        """
        try:
            original_price = order.price
            execution_price = original_price
            
            # Step 1: Simulate order latency - price may have changed
            if self.enable_latency:
                new_price = await self._simulate_order_latency(order.symbol)
                if new_price and new_price > 0:
                    execution_price = new_price
                    logger.debug(
                        f"Price after latency: ${original_price:.3f} → ${execution_price:.3f} HKD "
                        f"({((execution_price/original_price - 1)*100):.3f}%)"
                    )
            
            # Step 2: Apply slippage (bid-ask spread + market movement)
            execution_price = self._calculate_slippage(execution_price, order.side)
            
            # Step 3: Apply market impact for large orders
            execution_price = self._calculate_market_impact(
                order.symbol, order.quantity, execution_price, order.side
            )
            
            # Update order with realistic execution price
            if execution_price != original_price:
                logger.info(
                    f"🎯 Realistic execution: {order.side.upper()} {order.symbol} - "
                    f"Expected: ${original_price:.3f} → Actual: ${execution_price:.3f} HKD "
                    f"(Slippage: {((execution_price/original_price - 1)*100):.3f}%)"
                )
            
            order.price = execution_price
            
            # Now proceed with normal order filling logic
            notional = order.quantity * execution_price
            fees = self.calculate_fees(notional, order.side)
            
            if order.side == "buy":
                total_cost = notional + fees
                
                # Check if we have sufficient balance
                if total_cost > self.balance:
                    logger.warning(
                        f"Insufficient balance to fill buy order: need ${total_cost:,.2f} HKD, "
                        f"have ${self.balance:,.2f} HKD"
                    )
                    order.status = OrderStatus.REJECTED
                    return False
                
                # Deduct from balance
                self.balance -= total_cost
                
                # Update position
                if order.symbol in self.positions:
                    old_qty = self.positions[order.symbol]["quantity"]
                    old_price = self.positions[order.symbol]["entry_price"]
                    
                    new_qty = old_qty + order.quantity
                    new_avg_price = (old_qty * old_price + notional) / new_qty
                    
                    self.positions[order.symbol]["quantity"] = new_qty
                    self.positions[order.symbol]["entry_price"] = new_avg_price
                    
                    logger.info(
                        f"📊 Updated position: {order.symbol} - "
                        f"{old_qty} → {new_qty} shares @ ${new_avg_price:.2f} avg"
                    )
                else:
                    self.positions[order.symbol] = {
                        "quantity": order.quantity,
                        "entry_price": order.price,
                        "entry_time": order.created_at,
                    }
                    
                    logger.info(
                        f"📊 New position: {order.symbol} - "
                        f"{order.quantity} shares @ ${order.price:.2f}"
                    )
                
                # Log all positions after update
                logger.info(f"📊 Total positions now: {len(self.positions)}")
                for sym, pos in self.positions.items():
                    logger.info(f"   - {sym}: {pos['quantity']} shares @ ${pos['entry_price']:.2f}")
                
                order.filled_quantity = order.quantity
                order.filled_price = order.price
                order.status = OrderStatus.FILLED
                
                logger.info(
                    f"Buy order filled: {order.symbol} - {order.quantity} shares @ "
                    f"${order.price:.2f} HKD, fees=${fees:.2f} HKD"
                )
                
                # Record portfolio snapshot after buy
                self._record_portfolio_snapshot()
            
            elif order.side == "sell":
                # Check if we have sufficient position to sell
                if order.symbol not in self.positions:
                    logger.warning(
                        f"Cannot sell {order.symbol}: no position"
                    )
                    order.status = OrderStatus.REJECTED
                    return False
                
                if self.positions[order.symbol]["quantity"] < order.quantity:
                    logger.warning(
                        f"Insufficient position to fill sell order: need {order.quantity} shares, "
                        f"have {self.positions[order.symbol]['quantity']} shares"
                    )
                    order.status = OrderStatus.REJECTED
                    return False
                
                proceeds = notional - fees
                
                # Add to balance
                self.balance += proceeds
                
                # Update position
                if order.symbol in self.positions:
                    self.positions[order.symbol]["quantity"] -= order.quantity
                    
                    # Remove position if quantity reaches zero
                    if self.positions[order.symbol]["quantity"] <= 0:
                        del self.positions[order.symbol]
                
                order.filled_quantity = order.quantity
                order.filled_price = order.price
                order.status = OrderStatus.FILLED
                
                logger.info(
                    f"Sell order filled: {order.symbol} - {order.quantity} shares @ "
                    f"${order.price:.2f} HKD, fees=${fees:.2f} HKD, "
                    f"proceeds=${proceeds:.2f} HKD"
                )
                
                # Record portfolio snapshot after sell
                self._record_portfolio_snapshot()
            
            self.order_history.append(order)
            return True
        
        except Exception as e:
            logger.error(f"Failed to fill order: {e}")
            return False

    def _record_portfolio_snapshot(self):
        """Record current portfolio value for history tracking"""
        try:
            # Calculate total portfolio value
            total_cash = self.balance
            total_positions_value = sum(
                pos["quantity"] * pos.get("entry_price", 0)
                for pos in self.positions.values()
            )
            total_value = total_cash + total_positions_value
            
            # Record snapshot
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "total_value": total_value,
                "cash": total_cash,
                "positions_value": total_positions_value,
                "position_count": len(self.positions)
            }
            self.portfolio_history.append(snapshot)
            
            # Keep only last 1000 snapshots to avoid memory issues
            if len(self.portfolio_history) > 1000:
                self.portfolio_history = self.portfolio_history[-1000:]
                
        except Exception as e:
            logger.error(f"Failed to record portfolio snapshot: {e}")

    async def reset(self, initial_balance: float):
        """
        Reset paper trading to initial state.
        
        Args:
            initial_balance: New starting balance in HKD
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions.clear()
        self.orders.clear()
        self.order_history.clear()
        self.portfolio_history.clear()
        self._record_portfolio_snapshot()  # Record initial state after reset
        logger.info(f"HK Stock Paper Trading reset with balance: ${initial_balance:,.2f} HKD")
    
    def configure_realism(
        self,
        enable_slippage: Optional[bool] = None,
        enable_latency: Optional[bool] = None,
        enable_market_impact: Optional[bool] = None,
        slippage_bps_range: Optional[tuple] = None,
        latency_ms_range: Optional[tuple] = None,
        market_impact_threshold_lots: Optional[int] = None,
    ):
        """
        Configure realism simulation parameters.
        
        Args:
            enable_slippage: Enable/disable slippage simulation
            enable_latency: Enable/disable latency simulation
            enable_market_impact: Enable/disable market impact simulation
            slippage_bps_range: Tuple of (min, max) slippage in basis points
            latency_ms_range: Tuple of (min, max) latency in milliseconds
            market_impact_threshold_lots: Minimum lots for market impact to apply
        """
        if enable_slippage is not None:
            self.enable_slippage = enable_slippage
        if enable_latency is not None:
            self.enable_latency = enable_latency
        if enable_market_impact is not None:
            self.enable_market_impact = enable_market_impact
        
        if slippage_bps_range:
            self.slippage_bps_min, self.slippage_bps_max = slippage_bps_range
        
        if latency_ms_range:
            self.latency_ms_min, self.latency_ms_max = latency_ms_range
        
        if market_impact_threshold_lots:
            self.market_impact_threshold_lots = market_impact_threshold_lots
        
        logger.info(
            f"Realism configuration updated: "
            f"slippage={self.enable_slippage} ({self.slippage_bps_min}-{self.slippage_bps_max} bps), "
            f"latency={self.enable_latency} ({self.latency_ms_min}-{self.latency_ms_max} ms), "
            f"market_impact={self.enable_market_impact} (threshold: {self.market_impact_threshold_lots} lots)"
        )
    
    def get_realism_config(self) -> Dict[str, Any]:
        """
        Get current realism simulation configuration.
        
        Returns:
            Dictionary with realism settings
        """
        return {
            "slippage": {
                "enabled": self.enable_slippage,
                "min_bps": self.slippage_bps_min,
                "max_bps": self.slippage_bps_max,
                "description": f"{self.slippage_bps_min/100:.2f}% - {self.slippage_bps_max/100:.2f}%"
            },
            "latency": {
                "enabled": self.enable_latency,
                "min_ms": self.latency_ms_min,
                "max_ms": self.latency_ms_max,
                "description": f"{self.latency_ms_min}-{self.latency_ms_max}ms delay"
            },
            "market_impact": {
                "enabled": self.enable_market_impact,
                "threshold_lots": self.market_impact_threshold_lots,
                "bps_per_1000_lots": self.market_impact_bps_per_1000_lots,
                "description": f"Applies to orders > {self.market_impact_threshold_lots} lots"
            }
        }

