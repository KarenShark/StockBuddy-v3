"""Service façade for the super agent orchestration stage."""

from __future__ import annotations

from typing import Optional

from stockbuddy.core.types import UserInput

from .core import SuperAgent, SuperAgentOutcome


class SuperAgentService:
    """Thin wrapper to expose SuperAgent behaviour as a service."""

    def __init__(
        self, 
        super_agent: SuperAgent | None = None,
        agent_capabilities: Optional[str] = None
    ) -> None:
        """Initialize SuperAgentService.
        
        Args:
            super_agent: Optional pre-configured SuperAgent instance
            agent_capabilities: Optional agent capabilities description to pass to SuperAgent
        """
        if super_agent is not None:
            self._super_agent = super_agent
        else:
            self._super_agent = SuperAgent(agent_capabilities=agent_capabilities)

    @property
    def name(self) -> str:
        return self._super_agent.name

    async def run(self, user_input: UserInput) -> SuperAgentOutcome:
        return await self._super_agent.run(user_input)
