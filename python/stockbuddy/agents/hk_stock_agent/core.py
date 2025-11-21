"""HK Stock Trading Agent Core Implementation"""

from typing import Any, AsyncGenerator, Dict, Optional

from agno.agent import Agent
from loguru import logger

from stockbuddy.adapters.models import create_model_for_agent
from stockbuddy.agents.auto_trading_agent.exchanges import HKStockPaperTrading
from stockbuddy.config.manager import get_config_manager
from stockbuddy.core.agent.responses import streaming
from stockbuddy.core.types import BaseAgent, StreamResponse

from .prompts import HK_STOCK_AGENT_INSTRUCTIONS
from .tools import TOOLS, initialize_trading_system


class HKStockAgent(BaseAgent):
    """
    HK Stock Trading Agent for Hong Kong stock market analysis and trading.
    
    Features:
    - Real-time HK stock price monitoring
    - Technical analysis with trading signals
    - Paper trading simulation
    - Portfolio management
    - HK market-specific insights (AH premium, HK Connect flow)
    """

    def __init__(self, **kwargs):
        """Initialize the HK Stock Agent."""
        super().__init__(**kwargs)
        
        # Load agent configuration
        self.config_manager = get_config_manager()
        self.agent_config = self.config_manager.get_agent_config("hk_stock_agent")
        
        # Initialize paper trading exchange
        # Get initial capital from config or use default (1 million HKD)
        trading_config = self.agent_config.extra_config.get("trading", {}) if self.agent_config else {}
        initial_capital = trading_config.get("initial_capital", 1000000.0)
        self.exchange = HKStockPaperTrading(initial_balance=initial_capital)
        
        # Initialize trading system for tools
        initialize_trading_system(self.exchange)
        
        # Create Agno agent with tools
        self.agent = Agent(
            model=create_model_for_agent("hk_stock_agent"),
            tools=TOOLS,
            instructions=HK_STOCK_AGENT_INSTRUCTIONS,
        )
        
        logger.info(
            f"HKStockAgent initialized with paper trading "
            f"(initial capital: ${initial_capital:,.2f} HKD)"
        )

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """Stream HK stock trading responses."""
        logger.info(
            f"Processing HK stock query: {query[:100]}{'...' if len(query) > 100 else ''}"
        )

        try:
            response_stream = self.agent.arun(
                query,
                stream=True,
                stream_intermediate_steps=True,
                session_id=conversation_id,
            )
            
            logger.debug("🔍 Starting to consume response_stream events...")
            event_count = 0
            last_tool_name = None
            
            async for event in response_stream:
                event_count += 1
                logger.debug(f"🔍 Event #{event_count}: {event.event} - {type(event)}")
                
                if event.event == "RunContent":
                    content = event.content or ""
                    
                    # Check if RunContent contains thinking/reasoning
                    if content and len(content) < 500 and any(
                        keyword in content.lower()
                        for keyword in [
                            "需要",
                            "应该",
                            "will",
                            "going to",
                            "analyze",
                            "分析",
                            "check",
                            "检查",
                            "get",
                            "fetch",
                            "calculate",
                        ]
                    ):
                        logger.info(f"  └─ 🧠 Detected reasoning in RunContent: {content[:100]}...")
                        yield streaming.reasoning(content)
                    else:
                        logger.debug(f"  └─ RunContent: {content[:100] if content else 'None'}...")
                        yield streaming.message_chunk(content)
                
                elif event.event == "ToolCallStarted":
                    tool_name = (
                        event.tool.tool_name if hasattr(event, "tool") else "unknown_tool"
                    )
                    
                    # Extract tool arguments
                    tool_args = None
                    if hasattr(event, "tool"):
                        if hasattr(event.tool, "arguments"):
                            tool_args = str(event.tool.arguments)
                        elif hasattr(event.tool, "args"):
                            tool_args = str(event.tool.args)
                    
                    # Add reasoning before tool call
                    reasoning_messages = {
                        "get_hk_stock_price": "Getting real-time stock price...",
                        "analyze_hk_stock": "Analyzing stock with technical indicators...",
                        "execute_hk_stock_buy": "Executing buy order (paper trading)...",
                        "execute_hk_stock_sell": "Executing sell order (paper trading)...",
                        "get_hk_portfolio": "Retrieving portfolio status...",
                        "search_hk_stocks": "Searching for HK stocks...",
                    }
                    
                    reasoning_before = reasoning_messages.get(
                        tool_name,
                        f"Calling tool {tool_name}...",
                    )
                    
                    if tool_args:
                        reasoning_before += f"\n\nParameters: {tool_args}"
                    
                    logger.info(f"  └─ 🧠 Reasoning before tool call: {tool_name}")
                    yield streaming.reasoning(reasoning_before)
                    
                    logger.info(f"  └─ 🔧 Tool call started: {tool_name}")
                    yield streaming.tool_call_started(
                        event.tool.tool_call_id, tool_name, tool_args
                    )
                    last_tool_name = tool_name
                
                elif event.event == "ToolCallCompleted":
                    tool_name = (
                        event.tool.tool_name
                        if hasattr(event, "tool")
                        else last_tool_name or "tool"
                    )
                    
                    # Add reasoning after tool call completion
                    result_preview = ""
                    if hasattr(event, "tool") and hasattr(event.tool, "result"):
                        result_str = str(event.tool.result)
                        if len(result_str) > 200:
                            result_preview = result_str[:200] + "..."
                        else:
                            result_preview = result_str
                    
                    reasoning_after = f"Tool {tool_name} completed. Processing results..."
                    if result_preview:
                        reasoning_after += f"\n\nResult preview: {result_preview}"
                    
                    logger.info(f"  └─ 🧠 Reasoning after tool call: {tool_name}")
                    yield streaming.reasoning(reasoning_after)
                    
                    logger.info(f"  └─ ✅ Tool call completed: {tool_name}")
                    yield streaming.tool_call_completed(
                        event.tool.result, event.tool.tool_call_id, tool_name
                    )
                
                elif event.event == "RunReasoning" or (
                    hasattr(event, "reasoning") and event.reasoning
                ):
                    # Capture reasoning/thinking events from Agno
                    reasoning_text = (
                        getattr(event, "reasoning", None)
                        or getattr(event, "content", None)
                        or str(event)
                    )
                    logger.info(
                        f"  └─ 🧠 Reasoning: {reasoning_text[:100] if reasoning_text else 'None'}..."
                    )
                    yield streaming.reasoning(reasoning_text or "")
                
                else:
                    logger.debug(f"  └─ Unhandled event type: {event.event}")
            
            logger.debug(
                f"🔍 Finished consuming {event_count} events from response_stream"
            )

            yield streaming.done()
            logger.info("HK stock query processed successfully")

        except Exception as e:
            logger.error(f"Error processing HK stock query: {str(e)}")
            logger.exception("Full error details:")
            yield {"type": "error", "content": f"Error processing query: {str(e)}"}

    async def run(self, query: str, **kwargs) -> str:
        """Run HK stock agent and return response."""
        logger.info(
            f"Running HK stock agent with query: {query[:100]}{'...' if len(query) > 100 else ''}"
        )

        try:
            logger.debug("Starting HK stock agent processing")

            # Get the complete response from the agent
            response = await self.agent.arun(query)

            logger.info("HK stock agent query completed successfully")
            return response.content

        except Exception as e:
            logger.error(f"Error in HK stock agent run: {str(e)}")
            logger.exception("Full error details:")
            return f"Error: {str(e)}"
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Get current portfolio status.
        
        Returns:
            Dictionary with portfolio information
        """
        try:
            balance = await self.exchange.get_balance()
            positions = await self.exchange.get_open_positions()
            
            position_list = []
            total_value = 0
            
            for symbol, pos in positions.items():
                current_price = await self.exchange.get_current_price(symbol)
                if current_price and current_price > 0:
                    market_value = pos["quantity"] * current_price
                    total_value += market_value
                    
                    position_list.append({
                        "symbol": symbol,
                        "quantity": pos["quantity"],
                        "entry_price": pos["entry_price"],
                        "current_price": current_price,
                        "market_value": market_value,
                    })
            
            return {
                "cash": balance.get("HKD", 0),
                "positions": position_list,
                "total_assets": balance.get("HKD", 0) + total_value,
            }
        
        except Exception as e:
            logger.error(f"Error getting portfolio status: {e}")
            return {"error": str(e)}

