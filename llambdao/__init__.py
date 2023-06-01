from abc import ABC
from itertools import combinations
from typing import Any, Dict, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field


class AbstractObject(ABC, BaseModel):
    class Config:
        allow_arbitrary_types = True

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="unique identifier"
    )
    name: str = Field(default="", description="human readable name")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = self.name or self.__class__.__name__ + "-" + self.id


Metadata = Dict[Any, Any]


class Message(AbstractObject):
    body: str = Field(description="message contents")
    sender: Optional[str] = Field(description="sender identifier")
    recipient: Optional[str] = Field(description="recipient identifier")
    thread: Optional[str] = Field(default=None, description="conversation identifier")
    metadata: Metadata = Field(default_factory=dict, description="additional metadata")

    @classmethod
    def inform(cls, body: str, **kwargs):
        """Create an inform message, for informing a Node without needing a response."""
        metadata = {**kwargs.pop("metadata", {}), "action": "inform"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def query(cls, body: str, **kwargs):
        """Create a query message, for querying information."""
        metadata = {**kwargs.pop("metadata", {}), "action": "query"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def request(cls, body: str, **kwargs):
        """Create a request message, for actions."""
        metadata = {**kwargs.pop("metadata", {}), "action": "request"}
        return cls(**kwargs, body=body, metadata=metadata)

    @classmethod
    def reply_to(
        cls,
        to_message: "Message",
        with_body: str,
        and_metadata: Optional[Metadata] = None,
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
    """Nodes can be composed into graphs."""

    class Edge(AbstractObject):
        """Edges point to other nodes."""

        node: "Node" = Field()
        metadata: Optional[Metadata] = Field(default=None)

    edges: Dict[Any, Edge] = Field(default_factory=dict)

    def link(self, node: "Node", **metadata):
        self.edges[node.name] = self.Edge(node, metadata)

    def unlink(self, node: "Node"):
        del self.edges[node.name]

    def receive(self, message: Message) -> Optional[Message]:
        return getattr(self, message.action)(message)


class Router(Node):
    """
    Routers are simple nodes that route messages to other nodes.

    This is useful for creating a central point of contact for a graph.
    """

    def receiver(self, message: Message):
        recipient = message.recipient
        if recipient is None:
            raise ValueError("Message must have a recipient")

        edge = self.edges.get(recipient)
        if edge is None:
            raise ValueError(f"Unknown recipient: {recipient}")

        return edge.node

    def receive(self, message: Message) -> Optional[Message]:
        return self.receiver(message).receive(message)


class Graph(Router):
    """A Graph is a Node that links passed nodes."""

    def __init__(self, graph: Dict[Node, Set[Node]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            for edge in edges:
                node.link(edge)


class Circle(Router):
    """A Circle is a Graph that links its set of nodes bidirectionally."""

    def __init__(self, nodes: Set[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
        for node_lhs, node_rhs in combinations(nodes, 2):
            node_lhs.link(node_rhs)
            node_rhs.link(node_lhs)
