import itertools
from abc import ABC
from typing import Dict, Iterable, List

from pyee.base import EventEmitter

from llambdao.abstract import AbstractNode, Field
from llambdao.message import Message


class Node(AbstractNode):
    event_emitter: EventEmitter = Field(default_factory=EventEmitter, init=False)

    def link(self, to_node: "AbstractNode", **metadata):
        super().link(to_node, **metadata)
        self.event_emitter.emit("linked", to_node)

    def unlink(self, from_node: "AbstractNode"):
        super().unlink(from_node)
        self.event_emitter.emit("unlinked", from_node)

    def message(self, content: str, type: str, **metadata) -> Message:
        return Message(
            content=content,
            type=type,
            metadata=metadata,
            role=self.role,
            sender_id=self.id,
        )

    def reply_to(
        self, parent: Message, content: str, type: str = "response", **metadata
    ) -> Message:
        return Message(
            content=content,
            type=type,
            metadata=metadata,
            parent_id=parent.id,
            role=self.role,
            sender_id=self.id,
        )

    def receive(self, message: Message) -> Iterable[Message]:
        method = getattr(self, message.type, None)
        if not method:
            raise AttributeError(
                f"{self.__class__.__name__} does not have a method named {message.type}"
            )

        yield from method(message)


AbstractNode.Edge.update_forward_refs()


class SystemNode(Node):
    role = "system"


class AssistantNode(Node):
    role = "assistant"


class UserNode(Node, ABC):
    role = "user"


class GraphNode(SystemNode, ABC):
    def __init__(self, graph: Dict[Node, List[Node]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)

            for edge in edges:
                node.link(edge)


class SwarmNode(SystemNode):
    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)

    def do(self, message: Message) -> Iterable[Message]:
        yield from itertools.chain.from_iterable(
            edge.node.receive(message) for edge in self.edges.values()
        )


class GroupChatNode(SystemNode):
    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)

    def chat(self, message: Message):
        messages = [message]
        cursor = 0
        while cursor < len(messages):
            message_i = messages[cursor]
            for edge in self.edges.values():
                if edge.node.id == message_i.sender_id:
                    continue
                for message_j in edge.node.receive(message_i):
                    yield message_j
                    messages.append(message_j)
            cursor += 1
