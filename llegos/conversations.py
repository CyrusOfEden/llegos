from abc import ABC, abstractmethod
from itertools import permutations

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


class ConversationalAgentNetwork(AgentNetwork):
    agents: set[ConversationalAgent] = Field(min_items=2, allow_mutation=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (a_1, a_2, Converse) for (a_1, a_2) in permutations(self.agents, 2)
        )
