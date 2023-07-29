from abc import ABC, abstractmethod
from itertools import permutations

from llegos.asyncio import AsyncReply
from llegos.networks import AgentNetwork, EphemeralMessage, Field, NetworkAgent


class Dialog(EphemeralMessage):
    intent = "dialog"


class DialogAgent(NetworkAgent, ABC):
    @abstractmethod
    async def converse(self, message: Dialog) -> AsyncReply[Dialog]:
        ...

    @property
    def conversation_partners(self):
        network = self.network
        neighbors = network.neighbors(self)
        return [agent for agent in neighbors if network.has_edge(self, agent, Dialog)]


class DialogNetwork(AgentNetwork):
    agents: set[DialogAgent] = Field(min_items=2, allow_mutation=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (a_1, a_2, Dialog) for (a_1, a_2) in permutations(self.agents, 2)
        )
