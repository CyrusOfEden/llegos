from typing import Any, List

import yaml
from pydantic import Field

from llambdao.agent import AbstractAgent, AgentRequest, AgentResponse


class GOAL(AbstractAgent):
    beliefs: List[Any] = Field(default_factory=list)
    goals: List[Any] = Field(default_factory=list)
    strategy: List[Any] = Field(default_factory=list)
    rules: List[Any] = Field(default_factory=list)
    policy: List[Any] = Field(default_factory=list)

    @property
    def directive(self) -> str:
        config = dict(
            beliefs=self.beliefs,
            goals=self.goals,
            strategy=self.strategy,
            rules=self.rules,
            policy=self.policy,
        )
        return yaml.dump(config)

    def inform(self, params: AgentRequest) -> None:
        """A type of call that that doesn't produce a response"""
        raise NotImplementedError

    def request(self, params: AgentRequest) -> AgentResponse:
        """A synchronous call that produces a response"""
        raise NotImplementedError
