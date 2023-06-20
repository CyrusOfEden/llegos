from datetime import datetime
from textwrap import dedent
from typing import Iterable, List, Optional

import yaml
from pydantic import Field

from llambdao.node import AbstractObject, Node


class Message(AbstractObject):
    sender: Node = Field()
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reply_to: Optional["Message"] = Field()
    intent: Optional[str] = Field(
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
        return dedent(
            f"""\
            class: {self.__class__.__name__}
            id: {self.id}
            role: {self.role}
            reply_to: {self.reply_to.id if self.reply_to else "None"}
            sender: {self.sender.id}
            timestamp: {self.timestamp.isoformat()}
            intent: {self.intent}
            content: {self.content}
            metadata:
                {yaml.dumps(self.metadata)}
            """
        )

    @property
    def role(self):
        return self.sender.role


def message_chain(message: Message, height: Optional[int] = 12) -> Iterable[Message]:
    """Get the sequence of messages that led to this message."""
    if height < 1:
        raise ValueError("limit must be greater than 0")
    elif height == 1 or message.reply_to is None:
        yield message
    else:
        yield from message_chain(message.reply_to, height=height - 1)
        yield message


def message_list(message: Message, limit: Optional[int] = 12) -> List[Message]:
    """Get the list of messages that led to this message."""
    return list(message_chain(message, height=limit))
