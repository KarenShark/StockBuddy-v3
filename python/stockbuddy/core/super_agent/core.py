import asyncio
from enum import Enum
from typing import Optional

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from pydantic import BaseModel, Field

import stockbuddy.utils.model as model_utils_mod
from stockbuddy.core.super_agent.prompts import (
    SUPER_AGENT_EXPECTED_OUTPUT,
    SUPER_AGENT_INSTRUCTION,
)
from stockbuddy.core.types import UserInput
from stockbuddy.utils.env import agent_debug_mode_enabled

# Try to import DuckDuckGo tools, gracefully degrade if not available
try:
    from agno.tools.duckduckgo import DuckDuckGoTools
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False


class SuperAgentDecision(str, Enum):
    ANSWER = "answer"
    HANDOFF_TO_PLANNER = "handoff_to_planner"


class SuperAgentOutcome(BaseModel):
    # Note: decision field has no description to avoid JSON Schema strict mode conflict with $ref
    decision: SuperAgentDecision
    # Optional enriched result data
    answer_content: Optional[str] = Field(
        None, description="Optional direct answer when decision is 'answer'"
    )
    enriched_query: Optional[str] = Field(
        None, description="Optional concise restatement to forward to Planner"
    )
    recommended_agents: Optional[list[str]] = Field(
        None, description="List of recommended agent names to handle this query"
    )
    reason: Optional[str] = Field(None, description="Brief rationale for the decision")


class SuperAgent:
    """Lightweight Super Agent that triages user intent before planning.

    Routes queries to appropriate specialist agents based on query type and agent capabilities.
    """

    name: str = "SuperAgent"

    def __init__(self, agent_capabilities: Optional[str] = None) -> None:
        """Initialize Super Agent with knowledge of available specialist agents.
        
        Args:
            agent_capabilities: Formatted string describing available agents and their capabilities.
                              If None, uses default basic agent information.
        """
        model = model_utils_mod.get_model_for_agent("super_agent")
        
        # Initialize tools for Super Agent if available
        # DuckDuckGo provides web search capability for initial research
        tools = []
        if DUCKDUCKGO_AVAILABLE:
            try:
                tools = [DuckDuckGoTools(search=True, news=True, fixed_max_results=5)]
            except Exception:
                # Fallback if DuckDuckGoTools initialization fails
                tools = []
        
        # Format instructions with agent capabilities
        if agent_capabilities is None:
            agent_capabilities = self._get_default_agent_capabilities()
        
        instructions = SUPER_AGENT_INSTRUCTION.format(agent_capabilities=agent_capabilities)
        
        self.agent = Agent(
            model=model,
            tools=tools,  # Enable web search and news tools if available
            markdown=False,
            debug_mode=agent_debug_mode_enabled(),
            instructions=[instructions],
            # output format
            expected_output=SUPER_AGENT_EXPECTED_OUTPUT,
            output_schema=SuperAgentOutcome,
            use_json_mode=model_utils_mod.model_should_use_json_mode(model),
            # context - OPTIMIZED for speed
            db=InMemoryDb(),
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=2,  # Reduced from 5 to 2 for faster processing
            read_chat_history=True,
            enable_session_summaries=False,  # Disabled for speed (Super Agent should be fast)
        )
    
    def _get_default_agent_capabilities(self) -> str:
        """Return default agent capabilities description if none provided."""
        return """
- ResearchAgent: Analyzes SEC filings (10-K, 10-Q, 13F), extracts financial data, monitors institutional holdings
- NewsAgent: Real-time news search, breaking news monitoring, financial market news, scheduled notifications
- StrategyAgent: Investment strategy recommendations, trade signals, portfolio allocation advice
- HKStockAgent: Hong Kong stock trading (港股交易), HK stock price monitoring, technical analysis, paper trading, portfolio management for HK stocks
"""

    async def run(self, user_input: UserInput) -> SuperAgentOutcome:
        """Run super agent triage."""
        await asyncio.sleep(0)

        response = await self.agent.arun(
            user_input.query,
            session_id=user_input.meta.conversation_id,
            user_id=user_input.meta.user_id,
            add_history_to_context=True,
        )
        outcome = response.content
        if not isinstance(outcome, SuperAgentOutcome):
            model = self.agent.model
            model_description = f"{model.id} (via {model.provider})"
            answer_content = (
                f"SuperAgent produced a malformed response: `{outcome}`. "
                f"Please check the capabilities of your model `{model_description}` and try again later."
            )
            outcome = SuperAgentOutcome(
                decision=SuperAgentDecision.ANSWER,
                answer_content=answer_content,
            )
        return outcome
