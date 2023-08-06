from abc import ABC
from itertools import permutations

from llegos.ephemeral import EphemeralMessage, Reply
from llegos.networks import ActorNetwork, Field, NetworkActor


class StartDialog(EphemeralMessage):
    ...


class Dialog(EphemeralMessage):
    message: str = Field(include=True)


class EndDialog(EphemeralMessage):
    ...


class DialogActor(NetworkActor, ABC):
    receivable_messages: set[type[EphemeralMessage]] = Field(
        default={StartDialog, Dialog, EndDialog}, exclude=True
    )

    def start_dialog(self, s: StartDialog) -> Dialog:
        ...

    def dialog(self, d: Dialog) -> Reply[Dialog]:
        ...

    def end_dialog(self, e: EndDialog) -> None:
        ...


class DialogNetwork(ActorNetwork):
    agents: set[DialogActor] = Field(min_items=2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for a1, a2 in permutations(self.agents, 2):
            self.graph.add_edge(a1, a2)
