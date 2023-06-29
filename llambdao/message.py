from datetime import datetime
from textwrap import dedent
from typing import Literal, Optional, Union

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
        return yaml.dump(self.dict(), sort_keys=False)


class SystemMessage(Message):
    role: Role = Field(default="system")
    type: MessageType = Field(default="be")


class UserMessage(Message):
    role: Role = Field(default="user")


class AssistantMessage(Message):
    role: Role = Field(default="assistant")


class ChatMessage(Message):
    type: MessageType = Field(default="chat")
