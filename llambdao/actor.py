from typing import Any, Optional

import ray

from llambdao import Message, Node, Router


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

    Can be mixed in with AsyncNode to create an actor that runs in its own event loop.
    """

    def actor(self, namespace: Optional[str] = None) -> Actor:
        return Actor.options(
            namespace=namespace,
            name=self.name,
            get_if_exists=True
        ).remote(self)


class ActorRouter(Router):
    def receiver(self, message: Message):
        return super().receiver(message).actor
