from typing import Any, Iterable

import ray

from llm_net.gen import GenAgent, Message
from llm_net.gen_async import GenAsyncAgent


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


@ray.remote(max_restarts=3, max_task_retries=3, num_cpus=1)
class GenAsyncActor:
    node: GenAsyncAgent

    def __init__(self, node: GenAsyncAgent):
        self.node = node

    def property(self, prop: str) -> Any:
        return getattr(self.node, prop)

    async def areceive(self, message: Message):
        return await self.node.areceive(message)
