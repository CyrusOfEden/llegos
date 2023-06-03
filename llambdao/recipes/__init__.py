from abc import ABC
from typing import Dict, List

from pydantic import Field

from llambdao import Message, Node


class Router(Node):
    def receive(self, message: Message):
        yield from self.edges[message.recipient.id].node.receive(message)


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


class Chat(Node):
    messages: List[Message] = Field(default_factory=list)

    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    def receive(self, message: Message):
        messages = [message]
        while message := messages.pop():
            stop = yield message
            if stop:
                break
            self.messages.append(message)

            receivers = (
                edge.node for edge in set(self.edges.values()) - set([message.sender])
            )
            broadcast_message = Message(**message.dict(), sender=self)
            for node in receivers:
                for response in node.receive(broadcast_message):
                    messages.append(response)
