from typing import Any, AsyncIterable, Iterable, Optional

import ray

from gen_net.agents import AsyncGenAgent, GenAgent, Message
from gen_net.legos.networks import GenNetwork, llm_net


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


class GenActorNetwork(GenNetwork):
    def receive(self, message: Message) -> Iterable[Message]:
        agent: Optional[GenActor] = message.receiver
        if agent is None:
            return
        if agent not in self:
            raise ValueError(f"Receiver {agent.id} not in GenNetwork")

        self.emit("receive", message)

        previous_network = llm_net.set(self)
        try:
            for response in agent.receive.remote(message):
                if (yield response) == StopIteration:
                    break
                yield from self.receive(response)
        finally:
            llm_net.reset(previous_network)


@ray.remote(max_restarts=3, max_task_retries=3, num_cpus=1)
class GenAsyncActor:
    node: AsyncGenAgent

    def __init__(self, node: AsyncGenAgent):
        self.node = node

    def property(self, prop: str) -> Any:
        return getattr(self.node, prop)

    async def receive(self, message: Message):
        return await self.node.receive(message)


class GenAsyncActorNetwork(GenNetwork):
    async def receive(self, message: Message) -> AsyncIterable[Message]:
        agent: Optional[GenAsyncActor] = message.receiver
        if agent is None:
            return
        if agent not in self:
            raise ValueError(f"Receiver {agent.id} not in GenNetwork")

        self.emit("receive", message)

        previous_network = llm_net.set(self)
        try:
            async for response in agent.receive.remote(message):
                if (yield response) == StopIteration:
                    break
                async for response in self.receive(response):
                    yield response
        finally:
            llm_net.reset(previous_network)
