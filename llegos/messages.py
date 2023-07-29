from typing import TYPE_CHECKING, Iterable, Literal

from networkx import DiGraph

if TYPE_CHECKING:
    from llegos.ephemeral import EphemeralMessage

Intent = (
    str
    | Literal[
        "ack",
        "action",
        "ask",
        "backward",
        "be",
        "chat",
        "dialog",
        "do",
        "forward",
        "generate",
        "inform",
        "predict",
        "proxy",
        "query",
        "request",
        "response",
        "step",
    ]
)


class Ack(EphemeralMessage):
    intent: Intent = "ack"


class Action(EphemeralMessage):
    intent: Intent = "action"


class Ask(EphemeralMessage):
    intent: Intent = "ask"


class Backward(EphemeralMessage):
    intent: Intent = "backward"


class Be(EphemeralMessage):
    intent: Intent = "be"


class Chat(EphemeralMessage):
    intent: Intent = "chat"


class Dialog(EphemeralMessage):
    intent: Intent = "dialog"


class Do(EphemeralMessage):
    intent: Intent = "do"


class Forward(EphemeralMessage):
    intent: Intent = "forward"


class Generate(EphemeralMessage):
    intent: Intent = "generate"


class Inform(EphemeralMessage):
    intent: Intent = "inform"


class Predict(EphemeralMessage):
    intent: Intent = "predict"


class Proxy(EphemeralMessage):
    intent: Intent = "proxy"


class Query(EphemeralMessage):
    intent: Intent = "query"


class Request(EphemeralMessage):
    intent: Intent = "request"


class Response(EphemeralMessage):
    intent: Intent = "response"


class Step(EphemeralMessage):
    intent: Intent = "step"


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
        if message.reply_to:
            g.add_edge(message.reply_to, message)
    return g


def nearest_parent(message: EphemeralMessage, ancestor_cls: type[EphemeralMessage]):
    if not message.parent:
        return None
    elif isinstance(message.parent, ancestor_cls):
        return message.parent
    else:
        return nearest_parent(message.parent, ancestor_cls)


def message_path(
    message: EphemeralMessage, ancestor: EphemeralMessage, max_height: int = 256
) -> Iterable[EphemeralMessage]:
    if max_height <= 0:
        raise ValueError("invalid max_height")
    if max_height == 1 and message.parent is None or message.parent != ancestor:
        raise ValueError("ancestor not found")
    elif message.parent and message.parent != ancestor:
        yield from message_path(message.parent, ancestor, max_height - 1)
    yield message
