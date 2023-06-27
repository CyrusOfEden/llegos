from typing import Any, Optional

import ray

from llambdao.message import Message
from llambdao.node.actor import ActorNode


@ray.remote(max_task_retries=3, num_cpus=1)
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
