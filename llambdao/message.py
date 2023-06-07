from datetime import datetime
from typing import Optional

from pydantic import Field

from llambdao.abc import AbstractObject, Node


class Message(AbstractObject):
    sender: Node = Field()
    content: str = Field()
    action: Optional[str] = Field(
        include=["be", "do", "chat", "request", "inform", "proxy", "query"]
    )
    """
    be = "be this way", "act as if you are", etc.
    do = "do this thing", "perform this action", etc.
    chat = "chat about this topic", "talk about this topic", etc.
    request = "request this thing", "ask for this thing", etc.
    inform = "inform of new data", "tell about this thing", etc.
    proxy = "proxy this message to another node"
    query = "query for information"
    """
    reply_to: Optional["Message"] = Field()
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def role(self):
        return self.sender.role
