from typing import Any, Iterable

import ray

from llm_net.gen import GenAgent, Message


@ray.remote(max_restarts=3, max_task_retries=3, num_cpus=1)
class GenActor:
    node: GenAgent

    def __init__(self, node: GenAgent):
        self.node = node

    def receive(self, message: Message) -> Iterable[Message]:
        """For receiving messages"""
        return self.node.receive(message)

    def property(self, prop: str) -> Any:
        """For getting arbitrary properties on the node"""
        return getattr(self.node, prop)
