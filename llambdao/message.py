from datetime import datetime
from textwrap import dedent
from typing import Iterable, List, Literal, Optional, Union

import yaml
from pydantic import Field

from llambdao.abstract import AbstractObject
from llambdao.types import Role

MessageType = Union[
    str,
    Literal[
        "chat", "request", "response", "query", "inform", "proxy", "step", "be", "do"
    ],
]


class Message(AbstractObject):
    """
    Messages are used to send messages between nodes.
    """

    type: Optional[MessageType] = Field(
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
    parent_id: Optional[str] = Field(title="parent message id")
    sender_id: str = Field(title="sender node id")

    def __str__(self):
        return yaml.dumps(
            {
                "class": self.__class__.__name__,
                "id": self.id,
                "kind": self.type,
                "role": self.role,
                "content": self.content,
                "created_at": self.created_at.isoformat(),
                "parent_id": self.parent_id,
                "sender_id": self.sender_id,
                "metadata": self.metadata,
            }
        )


class SystemMessage(Message):
    role: Role = Field(default="system")
    type: MessageType = Field(default="be")


class HumanMessage(Message):
    role: Role = Field(default="user")


class AssistantMessage(Message):
    role: Role = Field(default="assistant")


class ChatMessage(Message):
    type: MessageType = Field(default="chat")


def message_iter(message: Message, height: int) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if message is None or height == 1:
        yield message
    else:
        yield from message_iter(message.parent_id, height=height - 1)
        yield message


def message_list(message: Message, height: int) -> List[Message]:
    """Get the list of messages that led to this message."""
    return list(message_iter(message, height=height))


def test_message_list():
    m1 = Message(content="Hello")
    m2 = Message(content="How are you?", parent_id=m1.id)
    m3 = Message(content="I'm good, thanks!", parent_id=m2.id)
    m4 = Message(content="That's great to hear!", parent_id=m3.id)

    # Test with a limit of 2
    assert message_list(m4, height=2) == [m3, m4]
    # Test with a limit of 3
    assert message_list(m4, height=3) == [m2, m3, m4]
    # Test with a limit of 4
    assert message_list(m4, height=4) == [m1, m2, m3, m4]
    # Test with a limit of 5 (should return the same as limit=4)
    assert message_list(m4, height=5) == [m1, m2, m3, m4]
