from abc import ABC
from functools import cached_property
from typing import Any, Dict, List, Union

import ray
from langchain.agents import Tool
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class BaseObject(BaseModel):
    class Config:
        allow_arbitrary_types = True


class AgentRequest(BaseObject):
    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]]


class AgentResponse(BaseObject):
    response: AIMessage


class AbstractAgent(ABC, BaseObject):
    # This is how we define the agent's behaviour
    directive: str = Field(...)
    tools: List[Tool] = Field(default_factory=list)
    actor_options: Dict[str, Any] = Field(default_factory=dict)

    @cached_property
    def actor(self):
        """starts an actor that runs in its own process - needed to call future"""
        AgentActor.options(**self.actor_options).remote(self)

    def as_tool(self) -> Tool:
        """returns a tool that can be used by another agent"""
        raise NotImplementedError

    def inform(self, params: AgentRequest) -> None:
        """A type of call that that doesn't produce a response"""
        raise NotImplementedError

    async def ainform(self, params: AgentRequest) -> None:
        """A type of call that that doesn't produce a response"""
        raise NotImplementedError

    def request(self, params: AgentRequest) -> AgentResponse:
        """A synchronous call that produces a response"""
        raise NotImplementedError

    async def arequest(self, params: AgentRequest) -> AgentResponse:
        """A synchronous call that produces a response"""
        raise NotImplementedError


@ray.remote(max_restarts=3, max_task_retries=2, max_concurrency=5)
class AgentActor(AbstractAgent):
    agent: AbstractAgent

    def __init__(self, agent: AbstractAgent):
        self.agent = agent

    def inform(self, params: AgentRequest) -> None:
        return self.agent.inform(params)

    def request(self, params: AgentRequest) -> AgentResponse:
        return self.agent.request(params)


AbstractAgent.update_forward_refs()
