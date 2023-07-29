from abc import ABC, abstractmethod
from itertools import combinations

from networkx import MultiGraph

from llegos.asyncio import AsyncReply
from llegos.networks import AgentNetwork, EphemeralMessage, Field, NetworkAgent


class Converse(EphemeralMessage):
    intent = "converse"


class ConversationalAgent(NetworkAgent, ABC):
    @abstractmethod
    async def converse(self, message: Converse) -> AsyncReply[Converse]:
        ...

    @property
    def conversation_partners(self):
        network = self.network
        neighbors = network.neighbors(self)
        return [agent for agent in neighbors if network.has_edge(self, agent, Converse)]


class PairwiseConversationAgentNetwork(AgentNetwork):
    agents: set[ConversationalAgent] = Field(min_items=2)
    graph: MultiGraph = Field(default_factory=MultiGraph, include=False, exclude=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (a_1, a_2, Converse) for (a_1, a_2) in combinations(self.agents, 2)
        )
