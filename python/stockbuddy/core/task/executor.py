import asyncio
import json
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Awaitable, Callable, Iterable, List, Optional

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from loguru import logger

from stockbuddy.core.agent.connect import RemoteConnections
from stockbuddy.core.agent.responses import EventPredicates
from stockbuddy.core.constants import (
    CURRENT_CONTEXT,
    DEPENDENCIES,
    LANGUAGE,
    METADATA,
    TIMEZONE,
    USER_PROFILE,
)
from stockbuddy.core.conversation.service import ConversationService
from stockbuddy.core.event.factory import ResponseFactory
from stockbuddy.core.event.router import RouteResult, SideEffectKind
from stockbuddy.core.event.service import EventResponseService
from stockbuddy.core.plan.models import ExecutionPlan
from stockbuddy.core.task.models import Task
from stockbuddy.core.task.service import DEFAULT_EXECUTION_POLL_INTERVAL, TaskService
from stockbuddy.core.task.temporal import calculate_next_execution_delay
from stockbuddy.core.types import (
    BaseResponse,
    ComponentType,
    ScheduledTaskComponentContent,
    StreamResponseEvent,
    SubagentConversationPhase,
)
from stockbuddy.utils.i18n_utils import get_current_language, get_current_timezone
from stockbuddy.utils.user_profile_utils import get_user_profile_metadata
from stockbuddy.utils.uuid import generate_item_id, generate_task_id


class ScheduledTaskResultAccumulator:
    """Collect streaming output for a scheduled task run."""

    def __init__(self, task: Task) -> None:
        self._task = task
        self._buffer: list[str] = []

    @property
    def enabled(self) -> bool:
        return self._task.is_scheduled()

    def consume(self, responses: Iterable[BaseResponse]) -> list[BaseResponse]:
        if not self.enabled:
            return list(responses)

        passthrough: list[BaseResponse] = []
        for resp in responses:
            event = resp.event

            if EventPredicates.is_message(event):
                payload = resp.data.payload
                content = payload.content if payload else None
                if content:
                    self._buffer.append(content)
                continue

            if EventPredicates.is_reasoning(event):
                continue

            if EventPredicates.is_tool_call(event):
                continue

            passthrough.append(resp)

        return passthrough

    def finalize(self, response_factory: ResponseFactory) -> Optional[BaseResponse]:
        if not self.enabled:
            return None

        content = "".join(self._buffer).strip()
        if not content:
            content = "Task completed without output."

        component_payload = ScheduledTaskComponentContent(
            result=content,
            create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )
        component_payload_json = component_payload.model_dump_json(exclude_none=True)

        return response_factory.schedule_task_result_component(
            task=self._task,
            content=component_payload_json,
        )


class TaskExecutor:
    """Execute tasks and plans while persisting streamed output."""

    def __init__(
        self,
        agent_connections: RemoteConnections,
        task_service: TaskService,
        event_service: EventResponseService,
        conversation_service: ConversationService,
        poll_interval: float = DEFAULT_EXECUTION_POLL_INTERVAL,
    ) -> None:
        self._agent_connections = agent_connections
        self._task_service = task_service
        self._event_service = event_service
        self._conversation_service = conversation_service
        self._poll_interval = poll_interval

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        thread_id: str,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[BaseResponse, None]:
        if plan.guidance_message:
            response = self._event_service.factory.message_response_general(
                event=StreamResponseEvent.MESSAGE_CHUNK,
                conversation_id=plan.conversation_id,
                thread_id=thread_id,
                task_id=generate_task_id(),
                content=plan.guidance_message,
                agent_name="Planner",
            )
            yield await self._event_service.emit(response)
            return

        # Check if any tasks have dependencies
        has_dependencies = any(task.depends_on for task in plan.tasks)
        
        if not has_dependencies:
            # No dependencies: execute sequentially (legacy behavior)
            for task in plan.tasks:
                async for response in self._execute_single_task_in_plan(
                    task, plan, thread_id, metadata
                ):
                    yield response
        else:
            # Has dependencies: execute with dependency-aware parallelism
            async for response in self._execute_plan_with_dependencies(
                plan, thread_id, metadata
            ):
                yield response

    async def _execute_plan_with_dependencies(
        self,
        plan: ExecutionPlan,
        thread_id: str,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[BaseResponse, None]:
        """Execute tasks respecting dependencies with parallel execution where possible."""
        # Build task lookup
        tasks_by_id = {task.task_id: task for task in plan.tasks}
        completed = set()
        in_progress = set()
        
        # Topological sort to get execution batches
        batches = self._build_execution_batches(plan.tasks)
        
        for batch in batches:
            # Execute all tasks in this batch in parallel
            tasks_to_execute = [
                task for task in batch 
                if all(dep_id in completed for dep_id in task.depends_on)
            ]
            
            if not tasks_to_execute:
                continue
                
            # Create async generators for each task
            task_generators = [
                self._execute_single_task_in_plan(task, plan, thread_id, metadata)
                for task in tasks_to_execute
            ]
            
            # Mark as in progress
            for task in tasks_to_execute:
                in_progress.add(task.task_id)
            
            # Merge and yield responses from all parallel tasks
            async for response in self._merge_task_responses(task_generators, tasks_to_execute):
                yield response
            
            # Mark as completed and send task_completed events
            for task in tasks_to_execute:
                in_progress.remove(task.task_id)
                completed.add(task.task_id)
                
                # Send task_completed event to frontend
                task_completed_event = self._event_service.factory.task_completed(
                    conversation_id=plan.conversation_id,
                    thread_id=thread_id,
                    task_id=task.task_id,
                    agent_name=task.agent_name,
                )
                yield await self._event_service.emit(task_completed_event)

    def _build_execution_batches(self, tasks: List[Task]) -> List[List[Task]]:
        """Build batches of tasks that can execute in parallel."""
        tasks_by_id = {task.task_id: task for task in tasks}
        batches = []
        remaining = set(task.task_id for task in tasks)
        completed = set()
        
        while remaining:
            # Find tasks whose dependencies are all completed
            ready = [
                tasks_by_id[task_id]
                for task_id in remaining
                if all(dep_id in completed for dep_id in tasks_by_id[task_id].depends_on)
            ]
            
            if not ready:
                # Circular dependency detected
                logger.error(f"Circular dependency detected in tasks: {remaining}")
                # Execute remaining tasks anyway to avoid hanging
                ready = [tasks_by_id[task_id] for task_id in remaining]
            
            batches.append(ready)
            for task in ready:
                remaining.remove(task.task_id)
                completed.add(task.task_id)
        
        return batches

    async def _merge_task_responses(
        self,
        task_generators: List[AsyncGenerator[BaseResponse, None]],
        tasks: List[Task],
    ) -> AsyncGenerator[BaseResponse, None]:
        """Merge responses from multiple task generators executing in parallel."""
        # Create tasks for each generator
        async def consume_generator(gen: AsyncGenerator[BaseResponse, None], task_id: str):
            responses = []
            try:
                async for response in gen:
                    responses.append(response)
            except Exception as e:
                logger.exception(f"Error in task {task_id}: {e}")
            return responses
        
        # Execute all generators in parallel
        results = await asyncio.gather(
            *[consume_generator(gen, task.task_id) for gen, task in zip(task_generators, tasks)],
            return_exceptions=False
        )
        
        # Yield all responses in order
        for responses in results:
            for response in responses:
                yield response

    async def _execute_single_task_in_plan(
        self,
        task: Task,
        plan: ExecutionPlan,
        thread_id: str,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[BaseResponse, None]:
        """Execute a single task within a plan (extracted from original execute_plan)."""
        for task in [task]:  # Keep original loop structure for single task
            subagent_component_id = generate_item_id()
            # Define a one-time emitter for subagent END component (used in two places)
            end_component_emitted = False

            async def emit_subagent_end_once() -> Optional[BaseResponse]:
                nonlocal end_component_emitted
                if not task.handoff_from_super_agent:
                    return None
                if end_component_emitted:
                    return None
                end_component_emitted = True
                return await self._emit_subagent_conversation_component(
                    plan.conversation_id,
                    thread_id,
                    task,
                    subagent_component_id,
                    SubagentConversationPhase.END,
                )

            if task.handoff_from_super_agent:
                await self._conversation_service.ensure_conversation(
                    user_id=plan.user_id,
                    conversation_id=task.conversation_id,
                    agent_name=task.agent_name,
                    title=task.title,
                )

                # Emit subagent conversation start component
                yield await self._emit_subagent_conversation_component(
                    plan.conversation_id,
                    thread_id,
                    task,
                    subagent_component_id,
                    SubagentConversationPhase.START,
                )

                thread_started = self._event_service.factory.thread_started(
                    conversation_id=task.conversation_id,
                    thread_id=thread_id,
                    user_query=task.query,
                )
                yield await self._event_service.emit(thread_started)

            try:
                await self._task_service.update_task(task)
                async for response in self._execute_task(
                    task,
                    thread_id,
                    metadata,
                    on_before_done=(
                        emit_subagent_end_once
                        if task.handoff_from_super_agent
                        else None
                    ),
                ):
                    yield response
            except Exception as exc:  # pragma: no cover - defensive logging
                error_msg = f"(Error) Error executing {task.task_id}: {exc}"
                logger.exception(error_msg)
                failure = self._event_service.factory.task_failed(
                    conversation_id=plan.conversation_id,
                    thread_id=thread_id,
                    task_id=task.task_id,
                    content=error_msg,
                    agent_name=task.agent_name,
                )
                yield await self._event_service.emit(failure)
            finally:
                if task.handoff_from_super_agent:
                    # Emit subagent conversation end component (only if not already emitted)
                    end_resp = await emit_subagent_end_once()
                    if end_resp is not None:
                        yield end_resp

    async def _emit_subagent_conversation_component(
        self,
        super_agent_conversation_id: str,
        thread_id: str,
        subagent_task: Task,
        component_id: str,
        phase: SubagentConversationPhase,
    ) -> BaseResponse:
        """Emit a subagent conversation component with the specified phase."""
        component_payload = json.dumps(
            {
                "conversation_id": subagent_task.conversation_id,
                "agent_name": subagent_task.agent_name,
                "phase": phase.value,
            }
        )
        component = self._event_service.factory.component_generator(
            conversation_id=super_agent_conversation_id,
            thread_id=thread_id,
            task_id=subagent_task.task_id,
            content=component_payload,
            component_type=ComponentType.SUBAGENT_CONVERSATION.value,
            component_id=component_id,
            agent_name=subagent_task.agent_name,
        )
        return await self._event_service.emit(component)

    async def _execute_task(
        self,
        task: Task,
        thread_id: str,
        metadata: Optional[dict] = None,
        *,
        on_before_done: Optional[
            Callable[[], Awaitable[Optional[BaseResponse]]]
        ] = None,
    ) -> AsyncGenerator[BaseResponse, None]:
        task_id = task.task_id
        conversation_id = task.conversation_id

        await self._task_service.start_task(task_id)

        exec_metadata = dict(metadata or {})
        exec_metadata.setdefault(METADATA, {})
        exec_metadata.setdefault(
            DEPENDENCIES,
            {
                USER_PROFILE: get_user_profile_metadata(task.user_id),
                CURRENT_CONTEXT: {},
                LANGUAGE: get_current_language(),
                TIMEZONE: get_current_timezone(),
            },
        )

        if task.is_scheduled():
            yield await self._event_service.emit(
                self._event_service.factory.schedule_task_controller_component(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    task=task,
                )
            )
            # Optionally emit a one-time subagent END before sending done
            if on_before_done is not None:
                maybe_resp = await on_before_done()
                if maybe_resp is not None:
                    yield maybe_resp
            yield await self._event_service.emit(
                self._event_service.factory.done(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                )
            )

        try:
            while True:
                async for response in self._execute_single_task_run(
                    task,
                    thread_id,
                    exec_metadata,
                ):
                    yield response

                if not task.is_scheduled():
                    break

                delay = calculate_next_execution_delay(task.schedule_config)
                if not delay:
                    break
                logger.info(
                    f"Scheduled task `{task.title}` ({task_id}) will re-execute in {delay} seconds."
                )

                await self._sleep_with_cancellation(task, delay)

                if task.is_finished():
                    logger.info(f"Task `{task.title}` ({task_id}) is finished.")
                    break

            await self._task_service.complete_task(task_id)
            completed = self._event_service.factory.task_completed(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                agent_name=task.agent_name,
            )
            yield await self._event_service.emit(completed)
        except Exception as exc:
            await self._task_service.fail_task(task_id, str(exc))
            raise
        finally:
            await self._event_service.flush_task_response(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
            )

    async def _execute_single_task_run(
        self,
        task: Task,
        thread_id: str,
        metadata: dict,
    ) -> AsyncGenerator[BaseResponse, None]:
        agent_name = task.agent_name
        task_start = time.time()
        logger.info(f"⏱️ [PERF] Task execution started: {agent_name} - Task ID: {task.task_id[:16]}")
        
        client = await self._agent_connections.get_client(agent_name)
        if not client:
            raise RuntimeError(f"Could not connect to agent {agent_name}")

        remote_response = await client.send_message(
            task.query,
            conversation_id=task.conversation_id,
            metadata=metadata,
        )

        accumulator = ScheduledTaskResultAccumulator(task)
        async for remote_task, event in remote_response:
            if event is None and remote_task.status.state == TaskState.submitted:
                task.remote_task_ids.append(remote_task.id)
                started = self._event_service.factory.task_started(
                    conversation_id=task.conversation_id,
                    thread_id=thread_id,
                    task_id=task.task_id,
                    agent_name=agent_name,
                    task_title=task.title or task.query,  # Use task title or query as description
                )
                yield await self._event_service.emit(started)
                continue

            if isinstance(event, TaskStatusUpdateEvent):
                route_result: RouteResult = await self._event_service.route_task_status(
                    task, thread_id, event
                )
                responses = accumulator.consume(route_result.responses)
                for resp in responses:
                    yield await self._event_service.emit(resp)
                for side_effect in route_result.side_effects:
                    if side_effect.kind == SideEffectKind.FAIL_TASK:
                        await self._task_service.fail_task(
                            task.task_id, side_effect.reason or ""
                        )
                if route_result.done:
                    return
                continue

            if isinstance(event, TaskArtifactUpdateEvent):
                logger.info(
                    "Received unexpected artifact update for task %s: %s",
                    task.task_id,
                    event,
                )
                continue

        final_component = accumulator.finalize(self._event_service.factory)
        if final_component is not None:
            yield await self._event_service.emit(final_component)

        task_duration = time.time() - task_start
        logger.info(f"⏱️ [PERF] Task execution completed: {agent_name} - Duration: {task_duration:.2f}s")

        return

    async def _sleep_with_cancellation(self, task: Task, delay: float) -> None:
        remaining = delay
        while remaining > 0:
            if task.is_finished():
                return
            sleep_for = min(self._poll_interval, remaining)
            await asyncio.sleep(sleep_for)
            remaining -= sleep_for
