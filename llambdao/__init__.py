from abc import ABC
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AbstractObject(ABC, BaseModel):
    class Config:
        allow_arbitrary_types = True

    id: str = Field(default_factory=lambda: str(uuid4()), description="unique identifier")
    name: str = Field(init=False, description="human readable name")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = self.name or self.__class__.__name__ + "-" + self.id


Metadata = Dict[str, Any]


class Message(AbstractObject):
    body: str = Field(description="message contents")
    sender: Optional[str] = Field(description="sender identifier")
    recipient: Optional[str] = Field(description="recipient identifier")
    thread: Optional[str] = Field(default=None, description="conversation identifier")
    metadata: Metadata = Field(default_factory=dict, description="additional metadata")

    @classmethod
    def inform(cls, body: str, **kwargs):
        """Create an inform message."""
        metadata = {**kwargs.pop("metadata", {}), "action": "inform"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def request(cls, body: str, **kwargs):
        """Create a request message."""
        metadata = {**kwargs.pop("metadata", {}), "action": "request"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def reply_to(
        cls, to_message: "Message", with_body: str, and_metadata: Optional[Metadata] = None
    ):
        """Create a reply to a message."""
        if and_metadata is not None:
            and_metadata.update(to_message.metadata)

        and_metadata.update(to_message.metadata)
        return cls(
            to=to_message.sender,
            sender=to_message.recipient,
            body=with_body,
            thread=to_message.thread,
            metadata=and_metadata,
        )

    @property
    def action(self) -> str:
        """
        The action of the message.

        Raises a KeyError if the message has no action.

        Usage:

        >>> message = Message.inform("Hello, world!")
        >>> message.action == "inform"
        True
        """
        return self.metadata["action"]


class Node(AbstractObject, ABC):
    class Edge(AbstractObject):
        node: "Node" = Field()
        metadata: Optional[Metadata] = Field(default=None)

    edges: Dict[str, Edge] = Field(default_factory=dict)

    def link(self, node: "Node", **metadata):
        self.edges[node.name] = self.Edge(node, metadata)

    def unlink(self, node: "Node"):
        del self.edges[node.name]

    def receive(self, message: Message) -> Optional[Message]:
        return getattr(self, message.action)(message)

