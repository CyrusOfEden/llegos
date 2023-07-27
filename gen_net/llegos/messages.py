from datetime import datetime
from textwrap import dedent
from typing import Iterable, Optional, Union

from networkx import DiGraph
from sorcery import delegate_to_attr

from gen_net.abstract import AbstractObject, Field
from gen_net.types import Method


class Message(AbstractObject):
    """
    Messages are used to send messages between nodes.
    """

    class Config(AbstractObject.Config):
        arbitrary_types_allowed = True
        json_encoders = {
            AbstractObject: lambda a: a.id,
        }

    intent: Union[str, Method] = Field(
        description=dedent(
            """\
            Agents call methods named after the intent of the message.

            A curated set of intents to consider:
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
            """
        ),
    )
    body: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender: Optional[AbstractObject] = Field(
        default=None, serialization_alias="sender_id"
    )
    receiver: Optional[AbstractObject] = Field(
        default=None, serialization_alias="receiver_id"
    )
    reply_to: Optional["Message"] = Field(
        default=None, serialization_alias="reply_to_id"
    )
    role = delegate_to_attr("sender")

    @staticmethod
    def reply(message: "Message", **kwargs) -> "Message":
        update = {
            "sender": message.receiver,
            "receiver": message.sender,
            "reply_to": message,
            "method": "reply",
            **kwargs,
        }
        return message.copy(update)

    @staticmethod
    def forward(message: "Message", **kwargs) -> "Message":
        update = {
            "sender": message.receiver,
            "reply_to": message,
            "body": message.body,
            **kwargs,
        }
        return message.copy(update)

    @classmethod
    @property
    def init_schema(cls):
        schema = super().init_schema()

        params = schema["parameters"]
        for key in ("reply_to", "sender", "receiver"):
            params[key] = {
                "title": params[key]["title"],
                "type": "string",
            }

        return schema


def messages_iter(message: Message, count: int = 12) -> Iterable[Message]:
    if message.reply and count > 0:
        yield from messages_iter(message.reply, count - 1)
    yield message


def messages_list(message: Message, count: int = 12) -> list[Message]:
    return list(messages_iter(message, count))


def messages_graph(messages: Iterable[Message]):
    g = DiGraph()
    for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g
