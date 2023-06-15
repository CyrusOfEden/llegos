import itertools
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from llambdao.message import Message

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

    def link(self, to_node: "Node", **metadata):
        self.edges[to_node.id] = self.Edge(to_node, metadata)

    def unlink(self, from_node: "Node"):
        del self.edges[from_node.id]

    def receive(self, message: "Message") -> Iterable["Message"]:
        yield from getattr(self, message.action)(message)


class Graph(Node, ABC):
    def __init__(self, graph: Dict[Node, List[Node]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)


class MapReduce(Node, ABC):
    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    def request(self, message: Message) -> Iterable[Message]:
        return self._reduce(message, self._map(message))

    def _map(self, message: Message) -> Iterable[Message]:
        sender = message.sender
        yield from itertools.chain.from_iterable(
            edge.node.receive(message)
            for edge in self.edges.values()
            if edge.node != sender
        )

    @abstractmethod
    def _reduce(
        self, message: Message, messages: Iterable[Message]
    ) -> Iterable[Message]:
        raise NotImplementedError()


class StableChat(MapReduce, ABC):
    def chat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            for message_j in self._map(message):
                message_j.reply_to = message_i
                yield message_j
                messages.append(message_j)

                message_i = message_j
