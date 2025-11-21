"""News Agent Core Implementation."""

from typing import Any, AsyncGenerator, Dict, Optional

from agno.agent import Agent
from loguru import logger

from stockbuddy.adapters.models import create_model_for_agent
from stockbuddy.config.manager import get_config_manager
from stockbuddy.core.agent.responses import streaming
from stockbuddy.core.types import BaseAgent, StreamResponse

from .prompts import NEWS_AGENT_INSTRUCTIONS
from .tools import get_breaking_news, get_financial_news, web_search


class NewsAgent(BaseAgent):
    """News Agent for fetching and analyzing news."""

    def __init__(self, **kwargs):
        """Initialize the News Agent."""
        super().__init__(**kwargs)
        # Load agent configuration
        self.config_manager = get_config_manager()
        self.agent_config = self.config_manager.get_agent_config("news_agent")

        # Load tools based on configuration
        available_tools = []

        available_tools.extend([web_search, get_breaking_news, get_financial_news])

        # Use create_model_for_agent to load agent-specific configuration
        self.knowledge_news_agent = Agent(
            model=create_model_for_agent("news_agent"),
            tools=available_tools,
            instructions=NEWS_AGENT_INSTRUCTIONS,
        )

        logger.info("NewsAgent initialized with news tools")

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """Stream news responses."""
        logger.info(
            f"Processing news query: {query[:100]}{'...' if len(query) > 100 else ''}"
        )

        try:
            response_stream = self.knowledge_news_agent.arun(
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
                    if content and len(content) < 500 and any(keyword in content.lower() for keyword in 
                        ['需要', '应该', 'will', 'going to', 'search', '查找', 'analyze', '分析', 'check', '检查']):
                        logger.info(f"  └─ 🧠 Detected reasoning in RunContent: {content[:100]}...")
                        yield streaming.reasoning(content)
                    else:
                        logger.debug(f"  └─ RunContent: {content[:100] if content else 'None'}...")
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
                    reasoning_before = f"Calling tool {tool_name} to search for news and information..."
                    if tool_args:
                        reasoning_before += f"\n\nSearch parameters: {tool_args}"
                    logger.info(f"  └─ 🧠 Reasoning before tool call: {tool_name}")
                    yield streaming.reasoning(reasoning_before)
                    
                    logger.info(f"  └─ 🔧 Tool call started: {tool_name}")
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
                    
                    reasoning_after = f"Tool {tool_name} completed. Analyzing and organizing search results..."
                    if result_preview:
                        reasoning_after += f"\n\nPreview: {result_preview}"
                    
                    logger.info(f"  └─ 🧠 Reasoning after tool call: {tool_name}")
                    yield streaming.reasoning(reasoning_after)
                    
                    logger.info(f"  └─ ✅ Tool call completed: {tool_name}")
                    yield streaming.tool_call_completed(
                        event.tool.result, event.tool.tool_call_id, tool_name
                    )
                elif event.event == "RunReasoning" or (hasattr(event, 'reasoning') and event.reasoning):
                    # Capture reasoning/thinking events from Agno
                    reasoning_text = getattr(event, 'reasoning', None) or getattr(event, 'content', None) or str(event)
                    logger.info(f"  └─ 🧠 Reasoning: {reasoning_text[:100] if reasoning_text else 'None'}...")
                    yield streaming.reasoning(reasoning_text or "")
                else:
                    logger.debug(f"  └─ Unhandled event type: {event.event}")
            logger.debug(f"🔍 Finished consuming {event_count} events from response_stream")

            yield streaming.done()
            logger.info("News query processed successfully")

        except Exception as e:
            logger.error(f"Error processing news query: {str(e)}")
            logger.exception("Full error details:")
            yield {"type": "error", "content": f"Error processing news query: {str(e)}"}

    async def run(self, query: str, **kwargs) -> str:
        """Run news agent and return response."""
        logger.info(
            f"Running news agent with query: {query[:100]}{'...' if len(query) > 100 else ''}"
        )

        try:
            logger.debug("Starting news agent processing")

            # Get the complete response from the knowledge news agent
            response = await self.knowledge_news_agent.arun(query)

            logger.info("News agent query completed successfully")
            logger.debug(f"Response length: {len(str(response.content))} characters")

            return response.content

        except Exception as e:
            logger.error(f"Error in NewsAgent run: {e}")
            logger.exception("Full error details:")
            return f"Error processing news query: {str(e)}"

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        logger.debug("Retrieving news agent capabilities")

        capabilities = {
            "name": "News Agent",
            "description": "Professional news agent for fetching and analyzing news",
            "tools": [
                {
                    "name": "web_search",
                    "description": "Search for general news and information",
                },
                {
                    "name": "get_breaking_news",
                    "description": "Get latest breaking news",
                },
                {
                    "name": "get_financial_news",
                    "description": "Get financial and market news",
                },
            ],
            "supported_queries": [
                "Latest news",
                "Breaking news",
                "Financial news",
                "Market updates",
                "Topic-specific news search",
            ],
        }

        logger.debug("Capabilities retrieved successfully")
        return capabilities
