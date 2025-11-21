"""Helper utilities for composing orchestrator service dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from stockbuddy.core.agent.connect import RemoteConnections
from stockbuddy.core.conversation import (
    ConversationManager,
    SQLiteConversationStore,
    SQLiteItemStore,
)
from stockbuddy.core.conversation.service import ConversationService
from stockbuddy.core.event.service import EventResponseService
from stockbuddy.core.plan.service import PlanService
from stockbuddy.core.super_agent import SuperAgentService
from stockbuddy.core.task.executor import TaskExecutor
from stockbuddy.core.task.locator import get_task_service
from stockbuddy.core.task.service import TaskService
from stockbuddy.utils import resolve_db_path


@dataclass(frozen=True)
class AgentServiceBundle:
    """Aggregate all services required by ``AgentOrchestrator``.

    The bundle guarantees that conversation-oriented objects share the same
    ``ConversationManager`` instance so that persistence is consistent even
    when individual services are overridden by callers. This also centralises
    the default construction logic, reducing the amount of dependency wiring
    inside the orchestrator itself.
    """

    agent_connections: RemoteConnections
    conversation_service: ConversationService
    event_service: EventResponseService
    task_service: TaskService
    plan_service: PlanService
    super_agent_service: SuperAgentService
    task_executor: TaskExecutor

    @classmethod
    def compose(
        cls,
        *,
        conversation_service: Optional[ConversationService] = None,
        event_service: Optional[EventResponseService] = None,
        plan_service: Optional[PlanService] = None,
        super_agent_service: Optional[SuperAgentService] = None,
        task_executor: Optional[TaskExecutor] = None,
    ) -> "AgentServiceBundle":
        """Create a bundle, constructing any missing services with defaults."""

        connections = RemoteConnections()

        if conversation_service is not None:
            conv_service = conversation_service
        elif event_service is not None:
            conv_service = event_service.conversation_service
        else:
            base_manager = ConversationManager(
                conversation_store=SQLiteConversationStore(resolve_db_path()),
                item_store=SQLiteItemStore(resolve_db_path()),
            )
            conv_service = ConversationService(manager=base_manager)

        event_service = event_service or EventResponseService(
            conversation_service=conv_service
        )
        # Prefer the process-local singleton for task service
        t_service = get_task_service()
        p_service = plan_service or PlanService(connections)
        
        # Create SuperAgentService with agent capabilities information
        if super_agent_service is None:
            agent_capabilities = cls._format_agent_capabilities(connections)
            sa_service = SuperAgentService(agent_capabilities=agent_capabilities)
        else:
            sa_service = super_agent_service
            
        executor = task_executor or TaskExecutor(
            agent_connections=connections,
            task_service=t_service,
            event_service=event_service,
            conversation_service=conv_service,
        )

        return cls(
            agent_connections=connections,
            conversation_service=conv_service,
            event_service=event_service,
            task_service=t_service,
            plan_service=p_service,
            super_agent_service=sa_service,
            task_executor=executor,
        )
    
    @classmethod
    def _format_agent_capabilities(cls, connections: RemoteConnections) -> str:
        """Format agent capabilities from RemoteConnections for Super Agent.
        
        Extracts agent descriptions and skills from loaded agent cards.
        """
        connections._ensure_remote_contexts_loaded()
        
        capabilities_lines = []
        for agent_name, context in connections._contexts.items():
            if context.local_agent_card is None:
                continue
            
            card = context.local_agent_card
            # Start with agent name and description
            capabilities_lines.append(f"\n{agent_name}:")
            if card.description:
                capabilities_lines.append(f"  Description: {card.description}")
            
            # Add skills if available
            if hasattr(card, 'skills') and card.skills:
                capabilities_lines.append("  Skills:")
                for skill in card.skills:
                    skill_dict = skill if isinstance(skill, dict) else skill.__dict__
                    skill_name = skill_dict.get('name', '')
                    skill_desc = skill_dict.get('description', '')
                    if skill_name:
                        capabilities_lines.append(f"    - {skill_name}: {skill_desc}")
        
        if not capabilities_lines:
            # Fallback to basic information if no agent cards loaded
            return """
- ResearchAgent: Analyzes SEC filings (10-K, 10-Q, 13F), extracts financial data, monitors institutional holdings
- NewsAgent: Real-time news search, breaking news monitoring, financial market news, scheduled notifications  
- StrategyAgent: Investment strategy recommendations, trade signals, portfolio allocation advice
"""
        
        return "\n".join(capabilities_lines)
