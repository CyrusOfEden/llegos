import itertools
from abc import ABC
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
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

    role: str = Field(include=["system", "user", "ai"], description="node role")
    edges: Dict[Any, Edge] = Field(default_factory=dict)

    def link(self, node: "Node", **metadata):
        self.edges[node.id] = self.Edge(node, metadata)

    def unlink(self, node: "Node"):
        del self.edges[node.id]

    def receive(self, message: "Message") -> Iterable["Message"]:
        yield from getattr(self, message.action)(message)


class Message(AbstractObject):
    sender: Node = Field(description="sender identifier")
    action: Optional[str] = Field(
        include=["be", "do", "chat"],
        description="message action",
    )
    content: str = Field(description="message contents")
    reply_to: Optional["Message"] = Field(description="reply to message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def role(self):
        return self.sender.role


class Graph(Node, ABC):
    def __init__(self, graph: Dict[Node, List[Node]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)

    def receive(self, message: Message):
        """Graphs should implement their own receive method."""
        raise NotImplementedError()


class MapReduce(Node, ABC):
    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    def receive(self, message: Message) -> Iterable[Message]:
        return self._reduce(self._map(message))

    def _map(self, message: Message) -> Iterable[Message]:
        sender = message.sender
        broadcast = Message(**message.dict(), sender=self)
        yield from itertools.chain.from_iterable(
            edge.node.receive(broadcast)
            for edge in self.edges.values()
            if edge.node != sender
        )

    def _reduce(self, messages: Iterable[Message]) -> Iterable[Message]:
        raise NotImplementedError()


class Chat(Node):
    messages: List[Message] = Field(default_factory=list)

    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    def receive(self, message: Message):
        messages = [message]
        while message := messages.pop():
            self.messages.append(message)

            broadcast = Message(**message.dict(), sender=self, action="tell")
            for edge in self.edges.values():
                if edge.node == message.sender:
                    continue
                for response in edge.node.receive(broadcast):
                    yield response
                    messages.append(response)
