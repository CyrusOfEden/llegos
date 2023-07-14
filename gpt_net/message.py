from datetime import datetime
from textwrap import dedent
from typing import AsyncIterable, Dict, Iterable, Optional, Union

from networkx import DiGraph
from pydantic import Field

from gpt_net.abstract import AbstractObject
from gpt_net.types import MessageTypes, Role


class Message(AbstractObject):
    """
    Messages are used to send messages between nodes.
    """

    type: Union[str, MessageTypes] = Field(
        description=dedent(
            """\
            By default, nodes will dispatch messages to a method named after the action.
            For example, a message with action "step" will call the "step" method.
            For async nodes, the method name will be prefixed with "a", so "step" becomes "astep".

            A curated set of kind names to consider:
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
    role: Role = Field()
    content: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reply_to_id: Optional[str] = Field(default=None, title="parent message id")
    from_id: Optional[str] = Field(default=None, title="sender node id")
    to_id: Optional[str] = Field(default=None, title="receiver node id")


class SystemMessage(Message):
    role: Role = "system"
    type: MessageTypes = "system"


class UserMessage(Message):
    role: Role = "user"


class AssistantMessage(Message):
    role: Role = "assistant"


class ChatMessage(Message):
    type: MessageTypes = "chat"


def compose_graph(messages: Iterable[Message]) -> DiGraph:
    g = DiGraph()
    lookup: Dict[str, Message] = {}
    for message in messages:
        lookup[message.id] = message
        if message.reply_to_id in lookup:
            g.add_edge(lookup[message.reply_to_id], message)
    return g


async def acompose_graph(messages: AsyncIterable[Message]) -> DiGraph:
    g = DiGraph()
    lookup: Dict[str, Message] = {}
    async for message in messages:
        lookup[message.id] = message
        if message.reply_to_id in lookup:
            g.add_edge(lookup[message.reply_to_id], message)
    return g
