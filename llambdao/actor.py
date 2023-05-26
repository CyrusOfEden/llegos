from typing import Any, Optional

import ray

from llambdao import Message, Node


@ray.remote(max_task_retries=3)
class Actor:
    """
    An internal class for wrapping a Node
    """

    node: "ActorNode"

    def __init__(self, node: "ActorNode"):
        self.node = node

    def receive(self, message: Message) -> Optional[Message]:
        """For receiving messages"""
        return self.node.receive(message)

    def property(self, prop: str) -> Any:
        """For getting arbitrary properties on the node"""
        return getattr(self.node, prop)

    def method(self, method: str, *args, **kwargs) -> Any:
        """For calling arbitrary methods on the node"""
        return getattr(self.node, method)(*args, **kwargs)


class ActorNode(Node):
    """
    Turn a node into a concurrent actor running in its own process.
    Learn more: https://docs.ray.io/en/latest/actors.html

    Usage:

    >>> from llambdao.ray import ray, Message, Node
    >>> class AsyncConcurrentHappyPrettyPrinterNode(AsyncNode, ActorNode):
    ...     name = "happy_pretty_printer"
    ...
    ...     from pprint import pprint
    ...
    ...     async def ainform(self, message: Message) -> None:
    ...         pprint(message.dict())
    ...
    ...     async def arequest(self, message: Message) -> Message:
    ...         return Message.reply_to(message, "HAPPY " + message.body.upper())
    ...
    >>> node = HappyPrettyPrinterNode()
    >>> node.receive(Message.inform("Hello, world!")) # Runs synchronously
    {'body': 'Hello, world!',
    'metadata': {'action': 'inform'},
    'recipient': None,
    'sender': None,
    'thread': None}
    >>> future = node.actor.areceive.remote(Message.request("Hello, world!")) # Runs asynchronously
    >>> print(42) # Prints immediately
    42
    >>> await future # Blocks until the future is ready
    {'body': 'HAPPY Hello, world!',
    'metadata': {'action': 'request'},
    'recipient': None,
    'sender': None,
    'thread': None}
    """

    def actor(self, namespace: Optional[str] = None) -> Actor:
        return Actor.options(
            namespace=namespace,
            name=self.name,
            get_if_exists=True
        ).remote(self)

