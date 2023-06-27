from datetime import datetime
from textwrap import dedent
from typing import Iterable, List, Optional

import yaml
from pydantic import Field

from llambdao.node.sync import AbstractObject, Node, SystemNode


class Message(AbstractObject):
    sender: Node = Field()
    recipient: Optional[Node] = Field(
        description=dedent(
            """\
            Useful for routing, but optional when sending messages directly to a node.
            """
        )
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reply_to: Optional["Message"] = Field()
    kind: Optional[str] = Field(
        description=dedent(
            """\
            By default, nodes will dispatch messages to a method named after the action.
            For example, a message with action "step" will call the "step" method.
            For async nodes, the method name will be prefixed with "a", so "step" becomes "astep".

            A curated set of intent names to consider:
            - chat = "chat about this topic", "talk about this topic", etc.
            - request = "request this thing", "ask for this thing", etc.
            - query = "query for information"
            - inform = "inform of new data", "tell about this thing", etc.
            - proxy = "route this message to another agent"
            - step = process the environment, a la multi agent reinforcement learning
            - be = "be this way", "act as if you are", etc.
            - do = "do this thing", "perform this action", etc.
            """
        ),
    )
    content: str = Field(default="")

    def __str__(self):
        return yaml.dumps(
            {
                "class": self.__class__.__name__,
                "id": self.id,
                "role": self.role,
                "reply_to": self.reply_to.id if self.reply_to else "None",
                "sender": self.sender.id,
                "timestamp": self.timestamp.isoformat(),
                "intent": self.intent,
                "content": self.content,
                "metadata": self.metadata,
            }
        )

    @property
    def role(self):
        return self.sender.role


class SystemMessage(Message):
    sender = SystemNode
    action = "be"


class ChatMessage(Message):
    action = "chat"


def message_iter(message: Message, height: Optional[int] = 12) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if height < 1:
        raise ValueError("limit must be greater than 0")
    elif height == 1 or message.reply_to is None:
        yield message
    else:
        yield from message_iter(message.reply_to, height=height - 1)
        yield message


def test_message_iter():
    m1 = Message("Hello")
    m2 = Message("How are you?", reply_to=m1)
    m3 = Message("I'm good, thanks!", reply_to=m2)
    m4 = Message("That's great to hear!", reply_to=m3)

    # Test with a limit of 2
    assert list(message_iter(m4, limit=2)) == [m3, m4]
    # Test with a limit of 3
    assert list(message_iter(m4, limit=3)) == [m2, m3, m4]
    # Test with a limit of 4
    assert list(message_iter(m4, limit=4)) == [m1, m2, m3, m4]
    # Test with a limit of 5 (should return the same as limit=4)
    assert list(message_iter(m4, limit=5)) == [m1, m2, m3, m4]


def message_list(message: Message, limit: Optional[int] = 12) -> List[Message]:
    """Get the list of messages that led to this message."""
    return list(message_iter(message, height=limit))


def test_message_list():
    m1 = Message("Hello")
    m2 = Message("How are you?", reply_to=m1)
    m3 = Message("I'm good, thanks!", reply_to=m2)
    m4 = Message("That's great to hear!", reply_to=m3)

    # Test with a limit of 2
    assert message_list(m4, limit=2) == [m3, m4]
    # Test with a limit of 3
    assert message_list(m4, limit=3) == [m2, m3, m4]
    # Test with a limit of 4
    assert message_list(m4, limit=4) == [m1, m2, m3, m4]
    # Test with a limit of 5 (should return the same as limit=4)
    assert message_list(m4, limit=5) == [m1, m2, m3, m4]
