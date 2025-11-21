import os
from typing import AsyncGenerator, Dict, Optional

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from edgar import set_identity
from loguru import logger

import stockbuddy.utils.model as model_utils_mod
from stockbuddy.agents.research_agent.hkex_tools import (
    fetch_hkex_policy_documents,
    fetch_hkex_rss_feed,
    search_hkex_policy,
)
from stockbuddy.agents.research_agent.knowledge import knowledge
from stockbuddy.agents.research_agent.prompts import (
    HK_RESEARCH_CONTEXT,
    KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
    KNOWLEDGE_AGENT_INSTRUCTION,
)
from stockbuddy.agents.research_agent.sources import (
    fetch_ashare_filings,
    fetch_event_sec_filings,
    fetch_periodic_sec_filings,
    web_search,
)
from stockbuddy.agents.utils.context import build_ctx_from_dep
from stockbuddy.core.agent import streaming
from stockbuddy.core.types import BaseAgent, StreamResponse
from stockbuddy.utils.env import agent_debug_mode_enabled


class ResearchAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Base tools (always available)
        tools = [
            fetch_periodic_sec_filings,
            fetch_event_sec_filings,
            fetch_ashare_filings,
            web_search,
            fetch_hkex_rss_feed,
            fetch_hkex_policy_documents,
            search_hkex_policy,
        ]

        # 🆕 Conditionally add Hong Kong market tools
        # Load HK-specific tools if enabled in configuration
        hk_tools = self._load_hong_kong_tools()
        hk_enabled = len(hk_tools) > 0

        if hk_tools:
            tools.extend(hk_tools)
            logger.info(f"Hong Kong market tools loaded: {len(hk_tools)} tools")

        # 🆕 Dynamically build instructions based on HK market enablement
        instructions = [KNOWLEDGE_AGENT_INSTRUCTION]
        if hk_enabled:
            instructions.append(HK_RESEARCH_CONTEXT)
            logger.info("Hong Kong market context added to instructions")

        self.knowledge_research_agent = Agent(
            model=model_utils_mod.get_model_for_agent("research_agent"),
            instructions=instructions,
            expected_output=KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
            tools=tools,
            knowledge=knowledge,
            db=InMemoryDb(),
            # context
            search_knowledge=True,
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=3,
            read_chat_history=True,
            enable_session_summaries=True,
            # configuration
            debug_mode=agent_debug_mode_enabled(),
        )
        set_identity(os.getenv("SEC_EMAIL"))

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        response_stream = self.knowledge_research_agent.arun(
            query,
            stream=True,
            stream_intermediate_steps=True,
            session_id=conversation_id,
            add_dependencies_to_context=True,
            dependencies=build_ctx_from_dep(dependencies),
        )
        # Track tool call sequence to add reasoning context
        last_tool_name = None
        
        async for event in response_stream:
            if event.event == "RunContent":
                # Check if RunContent contains thinking/reasoning before tool calls
                content = event.content or ""
                # If content seems like reasoning (short, planning-like), emit as reasoning
                if content and len(content) < 500 and any(keyword in content.lower() for keyword in 
                    ['需要', '应该', 'will', 'going to', 'search', '查找', 'analyze', '分析', 'check', '检查']):
                    logger.info(f"🧠 Detected reasoning in RunContent: {content[:100]}...")
                    yield streaming.reasoning(content)
                else:
                    yield streaming.message_chunk(content)
            elif event.event == "ToolCallStarted":
                tool_name = event.tool.tool_name if hasattr(event, 'tool') else "unknown_tool"
                # Extract tool arguments
                tool_args = None
                if hasattr(event, 'tool'):
                    if hasattr(event.tool, 'arguments'):
                        tool_args = str(event.tool.arguments)
                    elif hasattr(event.tool, 'args'):
                        tool_args = str(event.tool.args)
                
                # Add reasoning before tool call
                reasoning_before = f"Calling tool {tool_name} to retrieve relevant information..."
                if tool_args:
                    reasoning_before += f"\n\nParameters: {tool_args}"
                logger.info(f"🧠 Reasoning before tool call: {tool_name}")
                yield streaming.reasoning(reasoning_before)
                
                yield streaming.tool_call_started(
                    event.tool.tool_call_id, tool_name, tool_args
                )
                last_tool_name = tool_name
            elif event.event == "ToolCallCompleted":
                tool_name = event.tool.tool_name if hasattr(event, 'tool') else last_tool_name or "tool"
                # Add reasoning after tool call completion
                result_preview = ""
                if hasattr(event, 'tool') and hasattr(event.tool, 'result'):
                    result_str = str(event.tool.result)
                    if len(result_str) > 100:
                        result_preview = result_str[:100] + "..."
                    else:
                        result_preview = result_str
                
                reasoning_after = f"Tool {tool_name} completed. Analyzing results..."
                if result_preview:
                    reasoning_after += f"\n\nPreview: {result_preview}"
                
                logger.info(f"🧠 Reasoning after tool call: {tool_name}")
                yield streaming.reasoning(reasoning_after)
                
                yield streaming.tool_call_completed(
                    event.tool.result, event.tool.tool_call_id, tool_name
                )
            elif event.event == "RunReasoning" or (hasattr(event, 'reasoning') and event.reasoning):
                # Capture reasoning/thinking events from Agno
                reasoning_text = getattr(event, 'reasoning', None) or getattr(event, 'content', None) or str(event)
                logger.info(f"🧠 Reasoning captured: {reasoning_text[:100] if reasoning_text else 'None'}...")
                yield streaming.reasoning(reasoning_text or "")
        logger.info("Financial data analysis completed")

        yield streaming.done()

    def _load_hong_kong_tools(self) -> list:
        """
        条件加载港股市场工具

        根据 research_agent.yaml 中的 capabilities.hong_kong_market 配置
        决定是否加载港股数据工具。

        Returns:
            list: 港股工具列表，如果未启用则返回空列表
        """
        try:
            from stockbuddy.config.manager import get_config_manager

            # 获取 ResearchAgent 配置
            config_manager = get_config_manager()
            agent_config = config_manager.get_agent_config("research_agent")

            if not agent_config:
                logger.warning("ResearchAgent config not found, HK tools disabled")
                return []

            # 检查 hong_kong_market 配置
            hk_config = agent_config.capabilities.get("hong_kong_market", {})

            if not hk_config.get("enabled", False):
                logger.info("Hong Kong market features disabled in configuration")
                return []

            # 动态导入港股工具
            from stockbuddy.agents.research_agent.sources import (
                get_ah_premium,
                get_hk_capital_flow,
                get_hk_southbound_holdings,
            )

            hk_tools = []

            # 根据配置启用不同的工具
            if hk_config.get("southbound_flow", False):
                hk_tools.append(get_hk_capital_flow)
                hk_tools.append(get_hk_southbound_holdings)
                logger.info("Southbound capital flow tools enabled")

            if hk_config.get("ah_premium", False):
                hk_tools.append(get_ah_premium)
                logger.info("AH premium tool enabled")

            return hk_tools

        except Exception as e:
            logger.error(f"Failed to load Hong Kong tools: {e}")
            return []
