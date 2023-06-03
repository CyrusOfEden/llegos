from abc import ABC
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

Metadata = Dict[Any, Any]


class AbstractObject(ABC, BaseModel):
    class Config:
        allow_arbitrary_types = True

    id: str = Field(init=False, description="unique identifier")
    metadata: Metadata = Field(default_factory=dict, description="additional metadata")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = self.__class__.__name__ + "-" + str(uuid4())


class Node(AbstractObject, ABC):
    """Nodes can be composed into graphs."""

    class Edge(AbstractObject):
        """Edges point to other nodes."""

        node: "Node" = Field()
        metadata: Optional[Metadata] = Field(default=None)

    role: str = Field(
        default="", include=["system", "user", "ai"], description="node role"
    )
    edges: Dict[Any, Edge] = Field(default_factory=dict)

    def link(self, node: "Node", **metadata):
        self.edges[node.id] = self.Edge(node, metadata)

    def unlink(self, node: "Node"):
        del self.edges[node.id]

    def receive(self, message: "Message"):
        yield from getattr(self, message.action)(message)

    def draft_message(self, **kwargs) -> "Message":
        return Message(**kwargs, sender=self)


class Message(AbstractObject):
    sender: Node = Field(description="sender identifier")
    action: Optional[str] = Field(
        include=["inform", "query", "request"],
        description="message action",
    )
    content: str = Field(description="message contents")
    reply_to: Optional["Message"] = Field(description="reply to message")

    @property
    def role(self):
        return self.sender.role
