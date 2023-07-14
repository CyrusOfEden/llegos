from typing import Iterable

from networkx import DiGraph
from pyee import EventEmitter
from sorcery import delegate_to_attr

from gpt_net.abstract import AbstractObject, Field
from gpt_net.message import Message
from gpt_net.types import Role


class Node(AbstractObject):
    role: Role = Field(description="used to set the role for messages from this node")
    event_emitter: EventEmitter = Field(default_factory=EventEmitter, init=False)
    (
        add_listener,
        event_names,
        listeners,
        listens_to,
        on,
        once,
        remove_all_listeners,
        remove_listener,
    ) = delegate_to_attr("event_emitter")

    graph: DiGraph = Field(default_factory=DiGraph, exclude=True)
    (
        adj,
        succ,
        pred,
        successors,
        predecessors,
        edges,
        degree,
        clear_edges,
    ) = delegate_to_attr("graph")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graph.add_node(self)

    def add_edges(self, nodes: Iterable["Node"], **kwargs):
        for node in nodes:
            self.add_edge(node, **kwargs)

    def add_edge(self, node: "Node", **kwargs):
        self.graph.add_edge(self, node, **kwargs)

    def remove_edge(self, node: "Node"):
        self.graph.remove_edge(self, node)

    def remove_edges(self, nodes: Iterable["Node"]):
        for node in nodes:
            self.remove_edge(node)

    def message(self, content: str, type: str, **metadata) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            from_id=self.id,
            role=self.role,
            type=type,
            content=content,
            metadata=metadata,
        )

    def reply_to(
        self, message: Message, content: str, type: str = "response", **metadata
    ) -> Message:
        """Helper method for replying to a message with the node's role and id."""
        return Message(
            from_id=self.id,
            role=self.role,
            type=type,
            content=content,
            reply_to_id=message.id,
            metadata=metadata,
        )

    def receive(self, message: Message) -> Iterable[Message]:
        if message.from_id == self.id:
            return

        method = getattr(self, message.type, None)
        if not method:
            raise AttributeError(
                f"{self.__class__.__name__} does not have a method named {message.type}"
            )

        for self_response in method(message):
            if (yield self_response) == StopIteration:
                break
            for node in self.successors(self):
                for link_response in node.receive(self_response):
                    if (yield link_response) == StopIteration:
                        break


class SystemNode(Node):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"


class AssistantNode(Node):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class UserNode(Node):
    """Helper class for nodes whose messages should be set to role = user."""

    role = "user"
