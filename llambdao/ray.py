from typing import Optional

import ray
from pydantic import Field

from llambdao import Message
from llambdao import Node as SyncNode


@ray.remote(max_task_retries=3)
class Actor:
    """
    An internal class for wrapping a Node
    """

    node: SyncNode

    def __init__(self, node: SyncNode):
        self.node = node

    def connect(self, node: SyncNode, **metadata):
        self.node.connect(node, **metadata)

    def disconnect(self, node: SyncNode):
        self.node.disconnect(node)

    def route(self, message: Message) -> SyncNode:
        return self.node.route(message)

    def receive(self, message: Message) -> Optional[Message]:
        return self.node.receive(message)


class Node(SyncNode):
    """
    Turn a node into a concurrent actor running in its own process.
    Learn more: https://docs.ray.io/en/latest/actors.html

    Usage:

    >>> from llambdao.ray import ray, Message, Node
    >>> class HappyPrettyPrinterNode(Node):
    ...     namespace = "logs" # each ID is unique within its namespace
    ...     id = "happy_pretty_printer" # all calls will be routed to the same process
    ...
    ...     from pprint import pprint
    ...
    ...     def inform(self, message: Message) -> None:
    ...         pprint(message.dict())
    ...
    ...     def request(self, message: Message) -> Message:
    ...         return Message.reply_to(message, "HAPPY " + message.body.upper())
    ...
    >>> node = HappyPrettyPrinterNode()
    >>> node.receive(Message.inform("Hello, world!")) # Runs synchronously
    {'body': 'Hello, world!',
    'metadata': {'action': 'inform'},
    'recipient': None,
    'sender': None,
    'thread': None}
    >>> future = node.actor.receive(Message.request("Hello, world!")) # Runs asynchronously
    >>> print(42) # Prints immediately
    42
    >>> ray.get(future) # Blocks until the future is ready
    {'body': 'HAPPY Hello, world!',
    'metadata': {'action': 'request'},
    'recipient': None,
    'sender': None,
    'thread': None}
    """

    namespace: Optional[str] = Field(default=None)

    @property
    def actor(self) -> Actor:
        return Actor.options(
            namespace=self.namespace,
            name=self.id,
            get_if_exists=True
        ).remote(self)
