from typing import Any, Optional

import ray

from llambdao.abc.actor import ActorNode
from llambdao.message import Message


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
