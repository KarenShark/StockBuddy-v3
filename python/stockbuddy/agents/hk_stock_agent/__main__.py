import asyncio

from stockbuddy.agents.hk_stock_agent import HKStockAgent
from stockbuddy.core import create_wrapped_agent

if __name__ == "__main__":
    agent = create_wrapped_agent(HKStockAgent)
    asyncio.run(agent.serve())

