from datetime import datetime
from textwrap import dedent
from typing import Iterable, Optional, Union

from networkx import DiGraph
from pydantic import Field
from sorcery import dict_of

from gen_net.abstract import AbstractObject
from gen_net.types import Method, Role


class Message(AbstractObject):
    """
    Messages are used to send messages between nodes.
    """

    class Config(AbstractObject.Config):
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            AbstractObject: lambda a: a.id,
        }

    method: Union[str, Method] = Field(
        description=dedent(
            """\
            By default, nodes will dispatch messages to a method named after the action.
            For example, a message with action "step" will call the "step" method.
            For async nodes, the method name will be prefixed with "a", so "step" becomes "astep".

            A curated set of methods to consider:
            - chat = "chat about this topic", "talk about this topic", etc.
            - request = "request this thing", "ask for this thing", etc.
            - response = "responding with this thing", "replying with this thing", etc.
            - query = "query for information"
            - inform = "inform of new data", "tell about this thing", etc.
            - proxy = "route this message to another agent"
            - step = process the environment, a la multi agent reinforcement learning
            - be = "be this way", "act as if you are", etc.
            - do = "do this thing", "perform this action", etc.
            - check = "check if this is true", "verify this", etc.
            - log = "log this message", "record this message", etc.
            - info = "provide information about this thing"
            - warn = "warn about this thing"
            - error = "error about this thing"
            """
        ),
    )
    role: Role = Field()
    body: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender: Optional[AbstractObject] = Field(default=None, title="sender id")
    receiver: Optional[AbstractObject] = Field(default=None, title="receiver id")
    reply_to: Optional["Message"] = Field(default=None, title="reply to message")

    @classmethod
    def reply(cls, message: "Message", **kwargs) -> "Message":
        sender = message.receiver
        receiver = message.sender
        return cls(
            sender=sender,
            receiver=receiver,
            reply_to=message,
            role=sender.role,
            method="reply",
            **kwargs,
        )

    @classmethod
    def forward(
        cls, message: "Message", receiver: AbstractObject, **kwargs
    ) -> "Message":
        return cls(
            sender=message.receiver,
            receiver=receiver,
            reply_to=message,
            role=message.receiver.role,
            method="forward",
            **kwargs,
        )

    @classmethod
    @property
    def init_fn(cls):
        schema = cls.schema()

        parameters = schema["properties"]
        del parameters["id"]
        for key in ("reply_to", "sender", "receiver"):
            if key in parameters:
                parameters[key] = {
                    "title": parameters[key]["title"],
                    "type": "string",
                }

        name = cls.__name__
        description = cls.__doc__
        required = schema["required"]

        return dict_of(name, description, parameters, required)


def apply(message: Message) -> Iterable[Message]:
    agent = message.receiver
    if not agent:
        return
    for l1 in agent.receive(message):
        yield l1
        yield from apply(l1)


def messages_iter(message: Message, depth: int = 12) -> Iterable[Message]:
    if message.reply and depth > 0:
        yield from messages_iter(message.reply, depth - 1)
    yield message


def messages_list(message: Message, depth: int = 12) -> list[Message]:
    return list(messages_iter(message, depth))


def messages_graph(messages: Iterable[Message]) -> DiGraph:
    g = DiGraph()
    for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g
