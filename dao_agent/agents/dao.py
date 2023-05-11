from functools import cached_property
from typing import Dict, List

from langchain.agents import Tool
from pydantic import Field

from dao_agent.agent import AbstractAgent, AgentActor, AgentRequest, AgentResponse


class DAO(AbstractAgent):
    agents: List[AbstractAgent] = Field(default_factory=list)
    actors: Dict[int, AgentActor] = Field(default_factory=dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dao_tool = self.as_tool()
        for agent in enumerate(self.agents):
            agent.tools.append(dao_tool)

    @cached_property
    def actor(self):
        for index, agent in enumerate(self.agents):
            self.actors[index] = agent.actor

        return AgentActor.options(**self.actor_options).remote(self)

    def as_tool(self) -> Tool:
        # TODO — summarize self.agents into a description + call params, submit a plan
        description = """"""
        return Tool("DAO", description, run=self.request)

    def request(self, params: AgentRequest) -> AgentResponse:
        pass

    async def arequest(self, params: AgentRequest) -> AgentResponse:
        pass

    def inform(self, params: AgentRequest):
        for agent in self.agents:
            agent.inform(params)

    async def ainform(self, params: AgentRequest):
        for actor in self.actors.values():
            actor.inform.remote(params)
