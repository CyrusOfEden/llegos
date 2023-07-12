import itertools
from abc import ABC
from typing import Dict, Iterable, List, Optional, Union

from pyee.base import EventEmitter
from sorcery import delegate_to_attr

from llambdao.abstract import AbstractObject, Field
from llambdao.message import Message
from llambdao.types import Role


class Node(AbstractObject, ABC):
    """
    The base class for all nodes.
    """

    role: Role = Field(description="used to set the role for messages from this node")
    links: Dict[str, "Node"] = Field(
        default_factory=dict,
        description="connected nodes, in order of creation by default",
    )

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

    def __init__(self, links: Union[List["Node"], Dict[str, "Node"]] = [], **kwargs):
        super().__init__(**kwargs)

        if isinstance(links, list):
            for node in links:
                self.link(node)
        elif isinstance(links, dict):
            for name, node in links.items():
                self.link(node, name=name)
        else:
            raise TypeError(f"links must be a list or dict, not {type(links).__name__}")

    def link(self, to_node: "Node"):
        self.links[to_node.id] = to_node
        self.emit("linked", to_node)

    def unlink(self, from_node: Union[str, "Node"]):
        key = from_node if isinstance(from_node, str) else from_node.id
        unlinked_node = self.links.pop(key)
        self.emit("unlinked", key, unlinked_node)

    def message(
        self, content: str, type: str, parent_id: Optional[str] = None, **metadata
    ) -> Message:
        """Helper method for creating a message with the node's role and id."""
        return Message(
            content=content,
            type=type,
            metadata=metadata,
            parent_id=parent_id,
            from_id=self.id,
            role=self.role,
        )

    def reply_to(
        self, parent: Message, content: str, type: str = "response", **metadata
    ) -> Message:
        """Helper method for replying to a message with the node's role and id."""
        return self.message(content, type, parent_id=parent.id, **metadata)

    def receive(self, message: Message) -> Iterable[Message]:
        """
        This is the method that catches all incoming messages.

        By default, it will call a method named after the message's type.

        Typically, you will want to implement your own dispatching logic
        within one of the methods rather than the receive method.
        """

        method = getattr(self, message.type, None)
        if not method:
            raise AttributeError(
                f"{self.__class__.__name__} does not have a method named {message.type}"
            )

        yield from method(message)


class SystemNode(Node):
    """Helper class for nodes whose messages should be set to role = system."""

    role = "system"


class AssistantNode(Node):
    """Helper class for nodes whose messages should be set to role = assistant."""

    role = "assistant"


class UserNode(Node, ABC):
    """Helper class for nodes whose messages should be set to role = user."""

    role = "user"


class GraphNode(SystemNode, ABC):
    """
    Utility class for linking nodes together in a graph.
    """

    def __init__(self, graph: Dict[Node, List[Node]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)

            for edge in edges:
                node.link(edge)


class ApplicatorNode(SystemNode):
    """
    An ApplicatorNode applies its edge nodes to each message it receives,
    and then yields the results as a flattened iterator.
    """

    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)

    def do(self, message: Message) -> Iterable[Message]:
        yield from itertools.chain.from_iterable(
            edge.node.receive(message) for edge in self.links.values()
        )


class GroupChatNode(SystemNode):
    """
    A GroupChatNode broadcasts any received messages to all of its nodes,
    skipping the node that sent the message. Generated messages are continuously
    broadcasted until all nodes have processed all generated messages.
    """

    def __init__(self, nodes: List[Node], **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)

    def chat(self, message: Message):
        messages = [message]
        cursor = 0
        while cursor < len(messages):
            message_i = messages[cursor]
            for edge in self.links.values():
                if edge.node.id == message_i.from_id:
                    continue
                for message_j in edge.node.receive(message_i):
                    yield message_j
                    messages.append(message_j)
            cursor += 1


class AgencyNode(SystemNode):
    def receive(self, message: Message) -> Iterable[Message]:
        for response in super().receive(message):
            yield response
            if response.to_id == self.id:
                yield from self.receive(response)
            elif response.to_id in self.links:
                yield from self.links[response.to_id].receive(response)
