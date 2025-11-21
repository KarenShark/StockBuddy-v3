"""Planner: create execution plans from user input.

This module implements the ExecutionPlanner which uses an LLM-based
planning agent to convert a user request into a structured
`ExecutionPlan` consisting of `Task` objects. The planner supports
Human-in-the-Loop flows by emitting `UserInputRequest` objects (backed by
an asyncio.Event) when the planner requires clarification.

The planner is intentionally thin: it delegates reasoning to an AI agent
and performs JSON parsing/validation of the planner's output.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, List, Optional

from a2a.types import AgentCard
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb

import stockbuddy.utils.model as model_utils_mod
from stockbuddy.core.agent.connect import RemoteConnections
from stockbuddy.core.task.models import Task, TaskPattern, TaskStatus
from stockbuddy.core.types import UserInput
from stockbuddy.utils import generate_uuid
from stockbuddy.utils.env import agent_debug_mode_enabled
from stockbuddy.utils.uuid import generate_conversation_id

from .models import ExecutionPlan, PlannerInput, PlannerResponse, _TaskBrief
from .prompts import PLANNER_EXPECTED_OUTPUT, PLANNER_INSTRUCTION

logger = logging.getLogger(__name__)


class UserInputRequest:
    """
    Represents a request for user input during plan creation or execution.

    This class uses asyncio.Event to enable non-blocking waiting for user responses
    in the Human-in-the-Loop workflow.
    """

    def __init__(self, prompt: str):
        """Create a new request object for planner-driven user input.

        Args:
            prompt: Human-readable prompt describing the information needed.
        """
        self.prompt = prompt
        self.response: Optional[str] = None
        self.event = asyncio.Event()

    async def wait_for_response(self) -> str:
        """Block until a response is provided and return it.

        This is an awaitable helper designed to be used by planner code that
        wants to pause execution until the external caller supplies the
        requested value via `provide_response`.
        """
        await self.event.wait()
        return self.response

    def provide_response(self, response: str):
        """Supply the user's response and wake any waiter.

        Args:
            response: The text provided by the user to satisfy the prompt.
        """
        self.response = response
        self.event.set()


class ExecutionPlanner:
    """
    Creates execution plans by analyzing user input and determining appropriate agent tasks.

    This planner uses AI to understand user requests and break them down into
    executable tasks that can be handled by specific agents. It supports
    Human-in-the-Loop interactions when additional clarification is needed.
    """

    def __init__(
        self,
        agent_connections: RemoteConnections,
    ):
        self.agent_connections = agent_connections
        # Fetch model via utils module reference so tests can monkeypatch it reliably
        model = model_utils_mod.get_model_for_agent("super_agent")
        self.agent = Agent(
            model=model,
            tools=[
                # TODO: enable UserControlFlowTools when stable
                # UserControlFlowTools(),
                self.tool_get_agent_description,
                self.tool_get_enabled_agents,
            ],
            debug_mode=agent_debug_mode_enabled(),
            instructions=[PLANNER_INSTRUCTION],
            # output format
            markdown=False,
            output_schema=PlannerResponse,
            expected_output=PLANNER_EXPECTED_OUTPUT,
            use_json_mode=model_utils_mod.model_should_use_json_mode(model),
            # context - OPTIMIZED for speed
            db=InMemoryDb(),
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=3,  # Reduced from 5 to 3 for faster processing
            read_chat_history=True,
            enable_session_summaries=False,  # Disabled for speed (planning should be fast)
        )

    async def create_plan(
        self,
        user_input: UserInput,
        user_input_callback: Callable,
        thread_id: str,
        recommended_agents: Optional[list[str]] = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan from user input.

        This method orchestrates the planning agent run and returns a
        validated `ExecutionPlan` instance. The optional `user_input_callback`
        is called whenever the planner requests clarification; the callback
        should accept a `UserInputRequest` and arrange for the user's answer to
        be provided (typically by calling `UserInputRequest.provide_response`).

        Args:
            user_input: The user's request to be planned.
            user_input_callback: Async callback invoked with
                `UserInputRequest` instances when clarification is required.
            thread_id: Thread ID for this planning session.
            recommended_agents: Optional list of agent names recommended by Super Agent.

        Returns:
            ExecutionPlan: A structured plan with tasks for execution.
        """
        conversation_id = user_input.meta.conversation_id
        plan = ExecutionPlan(
            plan_id=generate_uuid("plan"),
            conversation_id=conversation_id,
            user_id=user_input.meta.user_id,
            orig_query=user_input.query,  # Store the original query
            created_at=datetime.now().isoformat(),
        )

        # Analyze input and create appropriate tasks
        tasks, guidance_message = await self._analyze_input_and_create_tasks(
            user_input,
            conversation_id,
            user_input_callback,
            thread_id,
            recommended_agents=recommended_agents,
        )
        plan.tasks = tasks
        plan.guidance_message = guidance_message

        return plan

    async def _analyze_input_and_create_tasks(
        self,
        user_input: UserInput,
        conversation_id: str,
        user_input_callback: Callable,
        thread_id: str,
        recommended_agents: Optional[list[str]] = None,
    ) -> tuple[List[Task], Optional[str]]:
        """
        Analyze user input and produce a list of `Task` objects.

        The planner delegates reasoning to an LLM agent which must output a
        JSON document conforming to `PlannerResponse`. If the planner pauses to
        request user input, the provided `user_input_callback` will be
        invoked for each requested field.

        Args:
            user_input: The original user input to analyze.
            conversation_id: Conversation this planning belongs to.
            user_input_callback: Async callback used for Human-in-the-Loop.
            recommended_agents: Optional list of agent names recommended by Super Agent.
            thread_id: Thread ID for this planning session.

        Returns:
            A tuple of (list of Task objects, optional guidance message).
            If plan is inadequate, returns empty list with guidance message.
        """
        # CRITICAL: If Super Agent recommended specific agents, USE THEM DIRECTLY
        # Don't rely on LLM planning which might fail - trust the Super Agent's routing decision
        if recommended_agents and len(recommended_agents) > 1:
            logger.info(
                f"Super Agent recommended {len(recommended_agents)} agents: {recommended_agents}. "
                f"Creating direct multi-agent plan without LLM."
            )
            # Create tasks directly based on Super Agent recommendations
            tasks = self._create_tasks_from_recommendations(
                user_input, recommended_agents, conversation_id, thread_id
            )
            return tasks, None
        
        # Build planner input with recommended agents hint for single-agent or no recommendation
        planner_query = user_input.query
        if recommended_agents and len(recommended_agents) == 1:
            # Single agent recommendation - add as hint
            logger.info(f"Planner received single agent recommendation: {recommended_agents[0]}")
            planner_query = f"{user_input.query}\n\n[Recommended Agent: {recommended_agents[0]}]"
        
        # Execute planning with the agent
        run_response = self.agent.run(
            PlannerInput(
                target_agent_name=user_input.target_agent_name,
                query=planner_query,
            ),
            session_id=conversation_id,
            user_id=user_input.meta.user_id,
        )

        # Handle user input requests through Human-in-the-Loop workflow
        while run_response.is_paused:
            for tool in run_response.tools_requiring_user_input:
                input_schema = tool.user_input_schema

                for field in input_schema:
                    # Use callback for async user input
                    # TODO: prompt options if available
                    request = UserInputRequest(field.description)
                    await user_input_callback(request)
                    user_value = await request.wait_for_response()
                    field.value = user_value

            # Continue agent execution with updated inputs
            run_response = self.agent.continue_run(
                # TODO: rollback to `run_id=run_response.run_id` when bug fixed by Agno
                run_response=run_response,
                updated_tools=run_response.tools,
            )

            if not run_response.is_paused:
                break

        # Parse planning result and create tasks
        plan_raw = run_response.content
        if not isinstance(plan_raw, PlannerResponse):
            # Fallback: try to manually parse the JSON response (handles trailing whitespace from gpt-5-mini)
            if isinstance(plan_raw, str):
                try:
                    import json
                    # Clean trailing whitespace and parse
                    cleaned_json = plan_raw.strip()
                    plan_dict = json.loads(cleaned_json)
                    plan_raw = PlannerResponse(**plan_dict)
                    logger.info(f"Successfully parsed JSON response after cleanup (length: {len(cleaned_json)} chars)")
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    model = self.agent.model
                    model_description = f"{model.id} (via {model.provider})"
                    return (
                        [],
                        (
                            f"Planner produced a malformed response: `{plan_raw[:500]}...`. "
                            f"Please check the capabilities of your model `{model_description}` and try again later."
                        ),
                    )
            else:
                model = self.agent.model
                model_description = f"{model.id} (via {model.provider})"
                return (
                    [],
                    (
                        f"Planner produced unexpected response type: {type(plan_raw)}. "
                        f"Please check the capabilities of your model `{model_description}` and try again later."
                    ),
                )
        logger.info(f"Planner produced plan: {plan_raw}")

        # Check if plan is inadequate or has no tasks
        if not plan_raw.adequate or not plan_raw.tasks:
            # Use guidance_message from planner, or fall back to reason
            guidance_message = plan_raw.guidance_message or plan_raw.reason
            logger.info(f"Planner needs user guidance: {guidance_message}")
            return [], guidance_message  # Return empty task list with guidance

        # Create tasks from planner response
        tasks = []
        # Check if this is a handoff from Super Agent
        # Super Agent name is "SuperAgent" - when user queries Super Agent, tasks should show subagent conversations
        is_super_agent_handoff = (
            user_input.target_agent_name == "SuperAgent" or
            not user_input.target_agent_name  # Empty target also means Super Agent routed
        )
        
        for t in plan_raw.tasks:
            tasks.append(
                self._create_task(
                    t,
                    user_input.meta.user_id,
                    conversation_id=user_input.meta.conversation_id,
                    thread_id=thread_id,
                    handoff_from_super_agent=is_super_agent_handoff,
                )
            )

        # Lightweight post-processing: For investment queries without explicit agent target,
        # if planner returned only 1 task, gently suggest multi-agent approach
        # This acts as a fallback to ensure comprehensive analysis
        if self._should_suggest_multi_agent_fallback(user_input, tasks):
            logger.info(
                f"Planner returned single task for complex query. "
                f"Suggesting multi-agent approach for comprehensive analysis."
            )
            tasks = self._create_multi_agent_fallback_plan(user_input, tasks[0], thread_id)

        return tasks, None  # Return tasks with no guidance message

    def _create_tasks_from_recommendations(
        self,
        user_input: UserInput,
        recommended_agents: list[str],
        conversation_id: str,
        thread_id: str,
    ) -> list[Task]:
        """Create tasks directly from Super Agent's agent recommendations.
        
        This bypasses LLM planning entirely and creates a structured plan based on
        the Super Agent's routing decision, ensuring reliable multi-agent execution.
        
        Args:
            user_input: Original user input
            recommended_agents: List of agent names recommended by Super Agent
            conversation_id: Conversation ID
            thread_id: Thread ID
            
        Returns:
            List of Task objects for execution
        """
        tasks = []
        query = user_input.query
        
        # Define task templates for common agent roles
        task_descriptions = {
            "ResearchAgent": f"研究和分析相关数据：{query}",
            "NewsAgent": f"搜索最新新闻和动态：{query}",
            "StrategyAgent": f"基于研究和新闻提供投资建议：{query}",
        }
        
        # Create parallel tasks for Research and News (no dependencies)
        independent_agents = [a for a in recommended_agents if a in ["ResearchAgent", "NewsAgent"]]
        dependent_agents = [a for a in recommended_agents if a == "StrategyAgent"]
        
        # Create independent tasks (can run in parallel)
        for agent_name in independent_agents:
            task_brief = _TaskBrief(
                task_id=generate_uuid("task"),
                agent_name=agent_name,
                title=task_descriptions.get(agent_name, query),
                query=query,
                pattern=TaskPattern.ONCE,
                schedule_config=None,
                depends_on=[],  # No dependencies - can run in parallel
            )
            task = self._create_task(
                task_brief,
                user_input.meta.user_id,
                conversation_id=conversation_id,
                thread_id=thread_id,
                handoff_from_super_agent=True,
            )
            tasks.append(task)
        
        # Create dependent tasks (depend on independent tasks)
        if dependent_agents and tasks:
            # Strategy Agent should wait for Research/News
            dependency_task_ids = [t.task_id for t in tasks]
            for agent_name in dependent_agents:
                task_brief = _TaskBrief(
                    task_id=generate_uuid("task"),
                    agent_name=agent_name,
                    title=task_descriptions.get(agent_name, query),
                    query=query,
                    pattern=TaskPattern.ONCE,
                    schedule_config=None,
                    depends_on=dependency_task_ids,  # Depends on research/news
                )
                task = self._create_task(
                    task_brief,
                    user_input.meta.user_id,
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    handoff_from_super_agent=True,
                )
                tasks.append(task)
        elif dependent_agents and not tasks:
            # No independent tasks, just run strategy directly
            for agent_name in dependent_agents:
                task_brief = _TaskBrief(
                    task_id=generate_uuid("task"),
                    agent_name=agent_name,
                    title=task_descriptions.get(agent_name, query),
                    query=query,
                    pattern=TaskPattern.ONCE,
                    schedule_config=None,
                    depends_on=[],
                )
                task = self._create_task(
                    task_brief,
                    user_input.meta.user_id,
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    handoff_from_super_agent=True,
                )
                tasks.append(task)
        
        logger.info(
            f"Created {len(tasks)} tasks from Super Agent recommendations: "
            f"{[t.agent_name for t in tasks]}"
        )
        return tasks
    
    def _should_suggest_multi_agent_fallback(
        self, user_input: UserInput, tasks: list
    ) -> bool:
        """Check if we should suggest multi-agent approach as fallback."""
        # Only apply to complex investment queries without explicit agent target
        if user_input.target_agent_name:
            return False
        if len(tasks) != 1:
            return False
        
        # Detect investment/analysis queries
        query_lower = (user_input.query or "").lower()
        investment_keywords = [
            "ipo", "product", "invest", "buy", "valuation", "trend", "should i",
            "worth", "recommendation", "compare", "vs", "versus", "analysis"
        ]
        chinese_keywords = ["投资", "值得", "买", "估值", "产品", "趋势", "分析", "对比"]
        
        return (
            any(kw in query_lower for kw in investment_keywords) or
            any(kw in user_input.query for kw in chinese_keywords)
        )

    def _create_multi_agent_fallback_plan(
        self, user_input: UserInput, original_task, thread_id: str
    ):
        """Create a comprehensive 3-agent plan as fallback."""
        from stockbuddy.core.task.models import Task, TaskStatus
        from stockbuddy.utils.uuid import generate_task_id
        
        base_query = user_input.query.strip()
        
        # Task 1: Research fundamentals (ResearchAgent)
        task1 = Task(
            task_id="fallback_task_1",
            conversation_id=original_task.conversation_id,
            thread_id=thread_id,
            user_id=original_task.user_id,
            agent_name="ResearchAgent",
            status=TaskStatus.PENDING,
            title="Fundamental Research",
            query=f"Research fundamental data, financial metrics, and market context: {base_query}",
            pattern=original_task.pattern,
            schedule_config=None,
            handoff_from_super_agent=original_task.handoff_from_super_agent,
            depends_on=[],
        )
        
        # Task 2: News and products (NewsAgent)
        task2 = Task(
            task_id="fallback_task_2",
            conversation_id=original_task.conversation_id,
            thread_id=thread_id,
            user_id=original_task.user_id,
            agent_name="NewsAgent",
            status=TaskStatus.PENDING,
            title="Latest News & Products",
            query=f"Collect latest news, product updates, and market sentiment: {base_query}",
            pattern=original_task.pattern,
            schedule_config=None,
            handoff_from_super_agent=original_task.handoff_from_super_agent,
            depends_on=[],
        )
        
        # Task 3: Strategy synthesis (StrategyAgent)
        task3 = Task(
            task_id="fallback_task_3",
            conversation_id=original_task.conversation_id,
            thread_id=thread_id,
            user_id=original_task.user_id,
            agent_name="StrategyAgent",
            status=TaskStatus.PENDING,
            title="Investment Recommendation",
            query=f"Based on research and news, provide investment recommendation with clear rationale: {base_query}",
            pattern=original_task.pattern,
            schedule_config=None,
            handoff_from_super_agent=original_task.handoff_from_super_agent,
            depends_on=["fallback_task_1", "fallback_task_2"],
        )
        
        return [task1, task2, task3]

    def _create_task(
        self,
        task_brief,
        user_id: str,
        conversation_id: str | None = None,
        thread_id: str | None = None,
        handoff_from_super_agent: bool = False,
    ) -> Task:
        """
        Create a new task for the specified agent.

        Args:
            conversation_id: Conversation this task belongs to
            user_id: User who requested this task
            agent_name: Name of the agent to execute the task
            query: Query/prompt for the agent
            pattern: Execution pattern (once or recurring)
            schedule_config: Schedule configuration for recurring tasks

        Returns:
            Task: Configured task ready for execution.
        """
        # task_brief is a _TaskBrief model instance

        # Reuse parent thread_id across subagent handoff.
        # When handing off from Super Agent, a NEW conversation_id is created for the subagent,
        # but we PRESERVE the parent thread_id to correlate the entire flow as one interaction.
        super_agent_conversation_id = None
        if handoff_from_super_agent:
            # Store the main conversation ID before generating a new one
            super_agent_conversation_id = conversation_id
            conversation_id = generate_conversation_id()
            logger.info(f"🔀 Sub-agent handoff: super_agent_conv={super_agent_conversation_id[:16]}, new_conv={conversation_id[:16]}")
            # Do NOT override thread_id here (keep the parent's thread_id per Spec A)

        return Task(
            task_id=task_brief.task_id,  # Use task_id from planner
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_id=user_id,
            agent_name=task_brief.agent_name,
            status=TaskStatus.PENDING,
            title=task_brief.title,
            query=task_brief.query,
            pattern=task_brief.pattern,
            schedule_config=task_brief.schedule_config,
            handoff_from_super_agent=handoff_from_super_agent,
            super_agent_conversation_id=super_agent_conversation_id,
            depends_on=task_brief.depends_on,  # Copy dependencies from task_brief
        )

    def tool_get_agent_description(self, agent_name: str) -> str:
        """
        Get the capabilities description of a specified agent by name.

        This function returns capability information for agents that can be used
        in the planning process to determine if an agent is suitable for a task.

        Args:
            agent_name: The name of the agent whose capabilities are to be retrieved

        Returns:
            str: A description of the agent's capabilities and supported operations.
        """
        if card := self.agent_connections.get_agent_card(agent_name):
            if isinstance(card, AgentCard):
                return agentcard_to_prompt(card)
            if isinstance(card, dict):
                return str(card)
            return agentcard_to_prompt(card)

        return "The requested agent could not be found or is not available."

    def tool_get_enabled_agents(self) -> str:
        map_agent_name_to_card = self.agent_connections.get_all_agent_cards()
        parts = []
        for agent_name, card in map_agent_name_to_card.items():
            parts.append(f"<{agent_name}>")
            parts.append(agentcard_to_prompt(card))
            parts.append((f"</{agent_name}>\n"))
        return "\n".join(parts)


def agentcard_to_prompt(card: AgentCard):
    """Convert an AgentCard to an LLM-friendly prompt string.

    Args:
        card: The AgentCard object or JSON structure describing an agent.

    Returns:
        A formatted string suitable for inclusion in the planner's instructions.
    """

    # Start with basic agent information
    prompt = f"# Agent: {card.name}\n\n"

    # Add description
    prompt += f"**Description:** {card.description}\n\n"

    # Add skills section
    if card.skills:
        prompt += "## Available Skills\n\n"

        for i, skill in enumerate(card.skills, 1):
            prompt += f"### {i}. {skill.name} (`{skill.id}`)\n\n"
            prompt += f"**Description:** {skill.description}\n\n"

            # Add examples if available
            if skill.examples:
                prompt += "**Examples:**\n"
                for example in skill.examples:
                    prompt += f"- {example}\n"
                prompt += "\n"

            # Add tags if available
            if skill.tags:
                tags_str = ", ".join([f"`{tag}`" for tag in skill.tags])
                prompt += f"**Tags:** {tags_str}\n\n"

            # Add separator between skills (except for the last one)
            if i < len(card.skills):
                prompt += "---\n\n"

    return prompt.strip()
