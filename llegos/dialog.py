from abc import ABC, abstractmethod
from itertools import permutations

from llegos.asyncio import AsyncReply
from llegos.ephemeral import EphemeralMessage
from llegos.networks import AgentNetwork, Field, NetworkAgent


class Dialog(EphemeralMessage):
    message: str


class DialogAgent(NetworkAgent, ABC):
    @property
    def dialog_agents(self):
        return self.receptive_agents(Dialog)

    @abstractmethod
    async def dialog(self, d: Dialog) -> AsyncReply[Dialog]:
        "Yield 0 or more messages"
        ...


class AgentDialogNetwork(AgentNetwork):
    agents: set[DialogAgent] = Field(min_items=2, allow_mutation=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (a_1, a_2, Dialog) for (a_1, a_2) in permutations(self.agents, 2)
        )
