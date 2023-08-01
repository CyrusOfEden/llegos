from typing import Iterable, Sequence, Union

from networkx import DiGraph

from llegos.ephemeral import EphemeralMessage


class UserMessage(EphemeralMessage):
    @property
    def role(self):
        return "user"


class SystemMessage(EphemeralMessage):
    @property
    def role(self):
        return "system"


class AssistantMessage(EphemeralMessage):
    @property
    def role(self):
        return "assistant"


class Chat(EphemeralMessage):
    content: str


class Ack(EphemeralMessage):
    ...


def message_chain(
    message: "EphemeralMessage", height: int = 12
) -> Iterable["EphemeralMessage"]:
    if message.parent and height > 1:
        yield from message_chain(message.parent, height - 1)
    yield message


def message_list(
    message: "EphemeralMessage", height: int = 12
) -> list["EphemeralMessage"]:
    return list(message_chain(message, height))


def message_graph(messages: Iterable[EphemeralMessage]):
    g = DiGraph()
    for message in messages:
        if message.parent:
            g.add_edge(message.parent, message)
    return g


def find_closest(
    cls: Union[Sequence[type[EphemeralMessage]], type[EphemeralMessage]],
    of_message: EphemeralMessage,
    max_height: int = 256,
):
    if max_height <= 0:
        raise ValueError("max_height must be positive")
    if max_height == 0:
        raise ValueError("ancestor not found")
    if not of_message.parent:
        return None
    elif isinstance(of_message.parent, cls):
        return of_message.parent
    else:
        return find_closest(of_message.parent, cls, max_height - 1)


def message_path(
    message: EphemeralMessage, ancestor: EphemeralMessage, max_height: int = 256
) -> Iterable[EphemeralMessage]:
    if max_height <= 0:
        raise ValueError("max_height most be positive")
    if max_height == 1 and message.parent is None or message.parent != ancestor:
        raise ValueError("ancestor not found")
    elif message.parent and message.parent != ancestor:
        yield from message_path(message.parent, ancestor, max_height - 1)
    yield message
