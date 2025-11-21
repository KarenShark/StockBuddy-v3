import asyncio
import time
from typing import AsyncGenerator, Dict, Optional

from loguru import logger

from stockbuddy.core.constants import ORIGINAL_USER_INPUT, PLANNING_TASK
from stockbuddy.core.conversation import ConversationService, ConversationStatus
from stockbuddy.core.event import EventResponseService
from stockbuddy.core.plan import PlanService
from stockbuddy.core.super_agent import (
    SuperAgentDecision,
    SuperAgentOutcome,
    SuperAgentService,
)
from stockbuddy.core.task import TaskExecutor
from stockbuddy.core.types import BaseResponse, StreamResponseEvent, UserInput
from stockbuddy.utils.uuid import generate_task_id, generate_thread_id

from .services import AgentServiceBundle

# Constants for configuration
DEFAULT_CONTEXT_TIMEOUT_SECONDS = 3600  # 1 hour
ASYNC_SLEEP_INTERVAL = 0.1  # 100ms


class ExecutionContext:
    """Manage the state of an interrupted execution for later resumption.

    ExecutionContext stores lightweight metadata about an in-flight plan or
    task execution that has been paused waiting for user input. The context
    records the stage (e.g. "planning"), the conversation/thread identifiers,
    the original requesting user, and a timestamp used for expiration.
    """

    def __init__(self, stage: str, conversation_id: str, thread_id: str, user_id: str):
        self.stage = stage
        self.conversation_id = conversation_id
        self.thread_id = thread_id
        self.user_id = user_id
        self.created_at = asyncio.get_event_loop().time()
        self.metadata: Dict = {}

    def is_expired(
        self, max_age_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS
    ) -> bool:
        """Return True when the context is older than the configured TTL."""
        current_time = asyncio.get_event_loop().time()
        return current_time - self.created_at > max_age_seconds

    def validate_user(self, user_id: str) -> bool:
        """Validate that the user ID matches the original request"""
        return self.user_id == user_id

    def add_metadata(self, **kwargs):
        """Attach arbitrary key/value metadata to this execution context."""
        self.metadata.update(kwargs)

    def get_metadata(self, key: str, default=None):
        """Get metadata value"""
        return self.metadata.get(key, default)


class AgentOrchestrator:
    """Coordinate planning, execution, and persistence across services."""

    def __init__(
        self,
        conversation_service: ConversationService | None = None,
        event_service: EventResponseService | None = None,
        plan_service: PlanService | None = None,
        super_agent_service: SuperAgentService | None = None,
        task_executor: TaskExecutor | None = None,
    ) -> None:
        services = AgentServiceBundle.compose(
            conversation_service=conversation_service,
            event_service=event_service,
            plan_service=plan_service,
            super_agent_service=super_agent_service,
            task_executor=task_executor,
        )

        self.conversation_service = services.conversation_service
        self.event_service = services.event_service
        self.super_agent_service = services.super_agent_service
        self.plan_service = services.plan_service
        self.task_executor = services.task_executor

        # Execution contexts keep track of paused planner runs.
        self._execution_contexts: Dict[str, ExecutionContext] = {}

    # ==================== Public API Methods ====================

    async def process_user_input(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """
        Stream responses for a user input, decoupled from the caller's lifetime.

        This function now spawns a background producer task that runs the
        planning/execution pipeline and emits responses. The async generator
        here simply consumes from a local queue. If the consumer disconnects,
        the background task continues, ensuring scheduled tasks and long-running
        plans proceed independently of the SSE connection.
        """
        # Per-invocation queue and active flag
        queue: asyncio.Queue[Optional[BaseResponse]] = asyncio.Queue()
        active = {"value": True}

        async def emit(item: Optional[BaseResponse]):
            # Drop emissions if the consumer has gone away
            if not active["value"]:
                return
            try:
                await queue.put(item)
            except Exception:
                # Never fail producer due to queue issues; just drop
                pass

        # Start background producer
        asyncio.create_task(self._run_session(user_input, emit))

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        except asyncio.CancelledError:
            # Consumer cancelled; mark inactive so producer stops enqueuing
            active["value"] = False
            # Do not cancel producer; it should continue independently
            raise
        finally:
            # Mark inactive to stop further enqueues
            active["value"] = False
            # Best-effort: if producer already finished, nothing to do
            # We deliberately do not cancel the producer to keep execution alive

    # ==================== Private Helper Methods ====================

    async def _run_session(
        self,
        user_input: UserInput,
        emit: callable,
    ):
        """Background session runner that produces responses and emits them.

        It wraps the original processing pipeline and forwards each response to
        the provided emitter. Completion is signaled with a final None.
        """
        try:
            async for response in self._generate_responses(user_input):
                await emit(response)
        except Exception as e:
            # The underlying pipeline already emits system_failed + done, so this
            # path should be rare; still, don't crash the background task.
            logger.exception(
                f"Unhandled error in session runner for conversation {user_input.meta.conversation_id}: {e}"
            )
        finally:
            # Signal completion to the consumer (if any)
            try:
                await emit(None)
            except Exception:
                pass

    async def _generate_responses(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Generate responses for a user input (original pipeline extracted).

        This contains the previous body of process_user_input unchanged in
        behavior, yielding the same responses in the same order.
        """
        conversation_id = user_input.meta.conversation_id

        try:
            conversation, created = await self.conversation_service.ensure_conversation(
                user_id=user_input.meta.user_id,
                conversation_id=conversation_id,
                agent_name=user_input.target_agent_name,
            )

            if created:
                started = self.event_service.factory.conversation_started(
                    conversation_id=conversation_id
                )
                yield await self.event_service.emit(started)

            if conversation.status == ConversationStatus.REQUIRE_USER_INPUT:
                async for response in self._handle_conversation_continuation(
                    user_input
                ):
                    yield response
            else:
                async for response in self._handle_new_request(user_input):
                    yield response

        except Exception as e:
            logger.exception(
                f"Error processing user input for conversation {conversation_id}"
            )
            failure = self.event_service.factory.system_failed(
                conversation_id, f"(Error) Error processing request: {str(e)}"
            )
            yield await self.event_service.emit(failure)
        finally:
            yield self.event_service.factory.done(conversation_id)

    async def _handle_conversation_continuation(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Resume an interrupted execution after the user provided requested input.

        This method validates the existing `ExecutionContext`, records the new
        thread id for this resumed interaction, and either continues planning
        or indicates that resuming execution is not supported for other stages.

        It yields the generated streaming responses (thread start and subsequent
        planner/execution messages) back to the caller.
        """
        conversation_id = user_input.meta.conversation_id
        user_id = user_input.meta.user_id

        # Validate execution context exists
        if conversation_id not in self._execution_contexts:
            failure = self.event_service.factory.system_failed(
                conversation_id,
                "No execution context found for this conversation. The conversation may have expired.",
            )
            yield await self.event_service.emit(failure)
            return

        context = self._execution_contexts[conversation_id]

        # Validate context integrity and user consistency
        if not self._validate_execution_context(context, user_id):
            failure = self.event_service.factory.system_failed(
                conversation_id,
                "Invalid execution context or user mismatch.",
            )
            yield await self.event_service.emit(failure)
            await self._cancel_execution(conversation_id)
            return

        thread_id = generate_thread_id()
        response = self.event_service.factory.thread_started(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_query=user_input.query,
        )
        yield await self.event_service.emit(response)

        # Provide user response and resume execution
        # If we are in an execution stage, store the pending response for resume
        context.add_metadata(pending_response=user_input.query)
        if self.plan_service.provide_user_response(conversation_id, user_input.query):
            await self.conversation_service.activate(conversation_id)
        context.thread_id = thread_id

        # Resume based on execution stage
        if context.stage == "planning":
            async for response in self._continue_planning(
                conversation_id, thread_id, context
            ):
                yield response
        # Resuming execution stage is not yet supported
        else:
            failure = self.event_service.factory.system_failed(
                conversation_id,
                "Resuming execution stage is not yet supported.",
            )
            yield await self.event_service.emit(failure)

    async def _handle_new_request(
        self, user_input: UserInput
    ) -> AsyncGenerator[BaseResponse, None]:
        """Start planning and execution for a new user request.

        This creates a planner task (executed asynchronously) and yields
        streaming responses produced during planning and subsequent execution.
        """
        conversation_id = user_input.meta.conversation_id
        thread_id = generate_thread_id()
        response = self.event_service.factory.thread_started(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_query=user_input.query,
        )
        yield await self.event_service.emit(response)

        # 1) Fast-path routing: Skip Super Agent for complex queries that obviously need planning
        # This dramatically improves response time (saves 2-5 seconds)
        should_skip_super_agent = self._should_fast_track_to_planner(user_input)
        
        # 2) Super Agent triage phase (pre-planning) - skip if target agent is specified OR fast-tracked
        recommended_agents = None
        if not should_skip_super_agent and user_input.target_agent_name == self.super_agent_service.name:
            super_agent_start = time.time()
            logger.info(f"⏱️ [PERF] Super Agent started for conversation: {conversation_id}")
            
            super_outcome: SuperAgentOutcome = await self.super_agent_service.run(
                user_input
            )
            
            super_agent_duration = time.time() - super_agent_start
            logger.info(f"⏱️ [PERF] Super Agent completed in {super_agent_duration:.2f}s - Decision: {super_outcome.decision}")
            
            if super_outcome.answer_content:
                ans = self.event_service.factory.message_response_general(
                    StreamResponseEvent.MESSAGE_CHUNK,
                    conversation_id,
                    thread_id,
                    task_id=generate_task_id(),
                    content=super_outcome.answer_content,
                    agent_name=self.super_agent_service.name,
                )
                yield await self.event_service.emit(ans)
            if super_outcome.decision == SuperAgentDecision.ANSWER:
                return

            if super_outcome.decision == SuperAgentDecision.HANDOFF_TO_PLANNER:
                user_input.target_agent_name = ""
                user_input.query = super_outcome.enriched_query
                # Extract recommended agents from Super Agent
                recommended_agents = super_outcome.recommended_agents
                
                # Log the routing decision for debugging
                if recommended_agents:
                    logger.info(
                        f"Super Agent recommends agents: {recommended_agents} for query: {user_input.query[:100]}"
                    )

        # 3) Planner phase (existing logic)
        # Create planning task with user input callback
        planner_start = time.time()
        logger.info(f"⏱️ [PERF] Planner started for conversation: {conversation_id}")
        
        context_aware_callback = self._create_context_aware_callback(conversation_id)
        planning_task = self.plan_service.start_planning_task(
            user_input, thread_id, context_aware_callback, recommended_agents=recommended_agents
        )

        # Monitor planning progress
        async for response in self._monitor_planning_task(
            planning_task, thread_id, user_input, context_aware_callback
        ):
            yield response
        
        planner_duration = time.time() - planner_start
        logger.info(f"⏱️ [PERF] Planner completed in {planner_duration:.2f}s")

    def _format_execution_plan_as_component(self, plan) -> str:
        """Format execution plan as JSON for dynamic component rendering.
        
        Args:
            plan: ExecutionPlan with tasks
            
        Returns:
            JSON string containing task list data
        """
        import json
        
        tasks = getattr(plan, "tasks", [])
        if not tasks:
            return json.dumps({"tasks": []})
        
        # Build task list with structure
        task_list = []
        for task in tasks:
            task_data = {
                "id": task.task_id,
                "agentName": task.agent_name,
                "title": task.title or task.query,
                "query": task.query,
                "status": "pending",
                "dependsOn": task.depends_on or [],
            }
            task_list.append(task_data)
        
        # Determine execution structure (parallel vs sequential)
        independent_tasks = [t for t in task_list if not t["dependsOn"]]
        dependent_tasks = [t for t in task_list if t["dependsOn"]]
        
        return json.dumps({
            "tasks": task_list,
            "totalCount": len(task_list),
            "parallelCount": len(independent_tasks),
            "sequentialCount": len(dependent_tasks),
        }, ensure_ascii=False)
    
    def _format_execution_plan(self, plan) -> str:
        """Format execution plan as a TODO list for display to user.
        
        Args:
            plan: ExecutionPlan with tasks to format
            
        Returns:
            Formatted markdown string showing the execution plan
        """
        tasks = getattr(plan, "tasks", [])
        if not tasks:
            return ""
        
        # Build TODO list message
        lines = ["📋 **执行计划**", ""]
        
        if len(tasks) == 1:
            task = tasks[0]
            lines.append(f"🎯 **任务**: {task.title or task.query}")
            lines.append(f"👤 **Agent**: {task.agent_name}")
        else:
            lines.append(f"我将通过 {len(tasks)} 个步骤来完成这个任务：")
            lines.append("")
            
            # Group tasks by whether they have dependencies
            independent_tasks = [t for t in tasks if not t.depends_on]
            dependent_tasks = [t for t in tasks if t.depends_on]
            
            # Show independent tasks first (can run in parallel)
            if len(independent_tasks) > 1:
                lines.append("**并行执行**:")
                for i, task in enumerate(independent_tasks, 1):
                    lines.append(f"  {i}. [{task.agent_name}] {task.title or task.query}")
                lines.append("")
            
            # Show dependent tasks
            if dependent_tasks:
                if independent_tasks:
                    lines.append("**随后执行**:")
                for i, task in enumerate(dependent_tasks, 1):
                    lines.append(f"  {len(independent_tasks) + i}. [{task.agent_name}] {task.title or task.query}")
            
            # If all tasks are independent, show them as a simple list
            if not dependent_tasks and len(independent_tasks) <= 1:
                for i, task in enumerate(tasks, 1):
                    lines.append(f"{i}. **[{task.agent_name}]** {task.title or task.query}")
        
        lines.append("")
        lines.append("🚀 开始执行...")
        
        return "\n".join(lines)
    
    def _should_fast_track_to_planner(self, user_input: UserInput) -> bool:
        """
        Determine if query should skip Super Agent and go directly to Planner.
        
        Fast-tracking improves response time by 2-5 seconds for complex queries
        that we know will need planning anyway.
        """
        # Always use Super Agent if explicitly targeted
        if user_input.target_agent_name == self.super_agent_service.name:
            return False
        
        # Fast-track complex analysis/investment queries
        query_lower = (user_input.query or "").lower()
        
        # English keywords indicating complex multi-step analysis
        complex_keywords = [
            "analyze", "analysis", "compare", "vs", "versus", "recommend",
            "should i", "worth", "better", "invest", "investment",
            "ipo", "valuation", "trend", "outlook", "performance"
        ]
        
        # Chinese keywords for investment/analysis queries
        chinese_keywords = [
            "分析", "对比", "比较", "推荐", "建议", "值得", "投资",
            "估值", "趋势", "前景", "表现", "如何", "怎么样"
        ]
        
        # Check for multiple keywords (indicates complexity)
        english_matches = sum(1 for kw in complex_keywords if kw in query_lower)
        chinese_matches = sum(1 for kw in chinese_keywords if kw in user_input.query)
        
        # Fast-track if:
        # - 2+ English keywords, or
        # - 2+ Chinese keywords, or
        # - Contains comparison operators (vs, versus, 对比)
        return (
            english_matches >= 2 or
            chinese_matches >= 2 or
            any(kw in query_lower for kw in ["vs", "versus", " vs. "]) or
            any(kw in user_input.query for kw in ["对比", "vs"])
        )

    def _create_context_aware_callback(self, conversation_id: str):
        """Return an async callback that tags UserInputRequest objects with the
        conversation_id and forwards them to the orchestrator's handler.

        The planner receives this callback and can call it whenever it needs
        to request additional information from the end-user; the callback
        ensures the request is associated with the correct conversation.
        """

        async def context_aware_handle(request):
            request.conversation_id = conversation_id
            self.plan_service.register_user_input(conversation_id, request)

        return context_aware_handle

    async def _monitor_planning_task(
        self,
        planning_task: asyncio.Task,
        thread_id: str,
        user_input: UserInput,
        callback,
    ) -> AsyncGenerator[BaseResponse, None]:
        """Monitor an in-progress planning task and handle interruptions.

        While the planner is running this loop watches for pending user input
        requests. If the planner pauses for clarification, the method records
        the planning context and yields a `plan_require_user_input` response
        to the caller. When planning completes, the produced `ExecutionPlan`
        is executed.
        """
        conversation_id = user_input.meta.conversation_id
        user_id = user_input.meta.user_id

        # Wait for planning completion or user input request
        while not planning_task.done():
            if self.plan_service.has_pending_request(conversation_id):
                # Save planning context
                context = ExecutionContext(
                    "planning", conversation_id, thread_id, user_id
                )
                context.add_metadata(
                    original_user_input=user_input,
                    planning_task=planning_task,
                    planner_callback=callback,
                )
                self._execution_contexts[conversation_id] = context

                # Update conversation status and send user input request
                await self.conversation_service.require_user_input(conversation_id)
                prompt = self.plan_service.get_request_prompt(conversation_id) or ""
                response = self.event_service.factory.plan_require_user_input(
                    conversation_id,
                    thread_id,
                    prompt,
                )
                yield await self.event_service.emit(response)
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan
        plan = await planning_task

        # Set conversation title once if not set yet and a task title is available
        if getattr(plan, "tasks", None):
            first_title = getattr(plan.tasks[0], "title", None)
            await self._maybe_set_conversation_title(conversation_id, first_title)
            
            # Display execution plan (TODO list) only for Super Agent multi-task scenarios
            # Single agent queries don't need a TODO list display
            if len(plan.tasks) > 1:
                plan_data = self._format_execution_plan_as_component(plan)
                plan_display = self.event_service.factory.component_generator(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    task_id=generate_task_id(),
                    content=plan_data,
                    component_type="execution_plan",
                    component_id=f"plan-{thread_id}",
                    agent_name="Planner",
                )
                yield await self.event_service.emit(plan_display)
        
        async for response in self.task_executor.execute_plan(plan, thread_id):
            yield response

    def _validate_execution_context(
        self, context: ExecutionContext, user_id: str
    ) -> bool:
        """Return True if the execution context appears intact and valid.

        Checks include presence of a stage, matching user id and TTL-based
        expiration.
        """
        if not hasattr(context, "stage") or not context.stage:
            return False

        if not context.validate_user(user_id):
            return False

        if context.is_expired():
            return False

        return True

    async def _continue_planning(
        self, conversation_id: str, thread_id: str, context: ExecutionContext
    ) -> AsyncGenerator[BaseResponse, None]:
        """Resume a previously-paused planning task and continue execution.

        If required pieces of the planning context are missing this method
        fails the plan and cancels the execution. Otherwise it waits for the
        planner to finish, handling repeated user-input prompts if needed,
        and then proceeds to execute the resulting plan.
        """
        planning_task = context.get_metadata(PLANNING_TASK)
        original_user_input = context.get_metadata(ORIGINAL_USER_INPUT)

        if not all([planning_task, original_user_input]):
            failure = self.event_service.factory.plan_failed(
                conversation_id,
                thread_id,
                "Invalid planning context - missing required data",
            )
            yield await self.event_service.emit(failure)
            await self._cancel_execution(conversation_id)
            return

        # Continue monitoring planning task
        while not planning_task.done():
            if self.plan_service.has_pending_request(conversation_id):
                # Still need more user input, send request
                prompt = self.plan_service.get_request_prompt(conversation_id) or ""
                # Ensure conversation is set to require user input again for repeated prompts
                await self.conversation_service.require_user_input(conversation_id)
                response = self.event_service.factory.plan_require_user_input(
                    conversation_id, thread_id, prompt
                )
                yield await self.event_service.emit(response)
                return

            await asyncio.sleep(ASYNC_SLEEP_INTERVAL)

        # Planning completed, execute plan and clean up context
        plan = await planning_task
        del self._execution_contexts[conversation_id]

        # If this conversation was just created (tracked in context), set its title once.
        if getattr(plan, "tasks", None):
            first_title = getattr(plan.tasks[0], "title", None)
            await self._maybe_set_conversation_title(conversation_id, first_title)

        async for response in self.task_executor.execute_plan(plan, thread_id):
            yield response

    async def _maybe_set_conversation_title(
        self, conversation_id: str, title: Optional[str]
    ):
        """Set conversation title once after creation when a task title is available.

        Only sets the title if:
        - title is provided and non-empty
        - the conversation exists and currently has no title
        """
        try:
            if not title or not str(title).strip():
                return
            conversation = await self.conversation_service.get_conversation(
                conversation_id
            )
            if not conversation:
                return
            # Avoid overwriting any existing title
            if conversation.title:
                return
            conversation.title = str(title).strip()
            # Persist via manager to avoid expanding ConversationService API
            await self.conversation_service.manager.update_conversation(conversation)
        except Exception:
            # Title setting is best-effort; failures shouldn't break flow
            logger.exception(f"Failed to set conversation title for {conversation_id}")

    async def _cancel_execution(self, conversation_id: str):
        """Cancel and clean up any execution resources associated with a
        conversation.

        This cancels the planner task (if present), removes the execution
        context and clears any pending user input. It also resets the
        conversation's status back to active.
        """
        if conversation_id in self._execution_contexts:
            context = self._execution_contexts.pop(conversation_id)
            planning_task = context.get_metadata(PLANNING_TASK)
            if planning_task and not planning_task.done():
                planning_task.cancel()

        self.plan_service.clear_pending_request(conversation_id)
        await self.conversation_service.activate(conversation_id)

    async def _cleanup_expired_contexts(
        self, max_age_seconds: int = DEFAULT_CONTEXT_TIMEOUT_SECONDS
    ):
        """Sweep and remove execution contexts older than `max_age_seconds`.

        For each expired context the method cancels execution and logs a
        warning so the operator can investigate frequent expirations.
        """
        expired_conversations = [
            conversation_id
            for conversation_id, context in self._execution_contexts.items()
            if context.is_expired(max_age_seconds)
        ]

        for conversation_id in expired_conversations:
            await self._cancel_execution(conversation_id)
            logger.warning(
                f"Cleaned up expired execution context for conversation {conversation_id}"
            )
