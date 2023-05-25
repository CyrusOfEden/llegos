from abc import ABCMeta
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AbstractObject(BaseModel, meta=ABCMeta):
    class Config:
        allow_arbitrary_types = True


Metadata = Dict[str, Any]


class Message(AbstractObject):
    body: str = Field(description="message contents")
    sender: Optional[str] = Field(description="sender identifier")
    recipient: Optional[str] = Field(description="recipient identifier")
    thread: Optional[str] = Field(default=None, description="conversation identifier")
    metadata: Optional[Metadata] = Field(default=None, description="additional metadata")

    @classmethod
    def inform(cls, *args, **kwargs):
        """Create an inform message."""
        metadata = {**kwargs.pop("metadata", {}), "action": "inform"}
        return cls(
            *args,
            **kwargs,
            metadata=metadata
        )

    @classmethod
    def request(cls, *args, **kwargs):
        """Create a request message."""
        metadata = {**kwargs.pop("metadata", {}), "action": "request"}
        return cls(
            *args,
            **kwargs,
            metadata=metadata
        )

    @classmethod
    def reply_to(
        cls, to_message: "Message", with_body: str, and_metadata: Metadata = {}
    ):
        """Create a reply to a message."""
        metadata = {**to_message.metadata, **and_metadata}
        return cls(
            to=to_message.sender,
            sender=to_message.recipient,
            body=with_body,
            thread=to_message.thread,
            metadata=metadata,
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



class Receiver(meta=ABCMeta):
    def receive(self, message: Message) -> Optional[Message]:
        raise NotImplementedError


class Node(AbstractObject):
    """
    A node in a network that can send and receive messages.

    Usage:

    >>> class HappyPrettyPrinterNode(Node):
    ...     from pprint import pprint
    ...
    ...     def inform(self, message: Message) -> None:
    ...         pprint(message.dict())
    ...
    ...     def request(self, message: Message) -> Message:
    ...         return Message.reply_to(message, "HAPPY " + message.body.upper())
    ...
    >>> node = HappyPrettyPrinterNode()
    >>> node.receive(Message.inform("Hello, world!"))
    {'body': 'Hello, world!',
    'metadata': {'action': 'inform'},
    'recipient': None,
    'sender': None,
    'thread': None}
    >>> node.receive(Message.request("Hello, world!"))
    {'body': 'HAPPY Hello, world!',
    'metadata': {'action': 'request'},
    'recipient': None,
    'sender': None,
    'thread': None}
    """

    class Connection(AbstractObject):
        receiver: Receiver = Field()
        metadata: Optional[Metadata] = Field(default=None)

    id: str = Field(default_factory=lambda: str(id(object())))
    connections: Dict[str, Connection] = Field(default_factory=dict)

    def connect(self, node: "Node", **metadata):
        self.connections[node.id] = self.Connection(node, metadata)

    def disconnect(self, node: "Node"):
        del self.connections[node.id]

    def route(self, message: Message) -> "Node":
        if message.recipient == self.id:
            return self
        return self.connections[message.recipient].node

    def receive(self, message: Message) -> Optional[Message]:
        handler = self.route(message)
        return handler.receive(message)

