from abc import ABC, abstractmethod
from itertools import permutations

from llegos.ephemeral import EphemeralMessage, Reply
from llegos.messages import Chat
from llegos.networks import AgentNetwork, Field, NetworkAgent


class Dialog(Chat):
    ...


class DialogAgent(NetworkAgent, ABC):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={Dialog}, exclude=True
    )

    @property
    def dialog_partners(self):
        return [
            agent for agent in self.relationships if Dialog in agent.receivable_messages
        ]

    @abstractmethod
    def dialog(self, d: Dialog) -> Reply[Dialog]:
        ...


class DialogNetwork(AgentNetwork):
    agents: set[DialogAgent] = Field(min_items=2, allow_mutation=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.graph.add_edges_from(
            (a_1, a_2, Dialog) for (a_1, a_2) in permutations(self.agents, 2)
        )
