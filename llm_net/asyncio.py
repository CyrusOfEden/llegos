from typing import AsyncIterable, Optional

from pydantic import Field
from pyee.asyncio import AsyncIOEventEmitter

from llm_net.base import GenAgent, GenNetwork, llm_net
from llm_net.message import Message


class AsyncGenAgent(GenAgent):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter, init=False
    )

    async def areceive(
        self, message: Optional[Message] = None
    ) -> AsyncIterable[Message]:
        if message is None or message.sender == self or message.receiver != self:
            raise StopAsyncIteration

        self.emit("receive", message)

        method = getattr(self, message.type) if message.type else self.call
        return method(message)


class AsyncGenNetwork(GenNetwork):
    async def areceive(self, message: Message) -> AsyncIterable[Message]:
        agent: Optional[AsyncGenAgent] = message.receiver
        if agent is None:
            return
        if agent not in self:
            raise ValueError(f"Receiver {agent.id} not in GenNetwork")

        self.emit("receive", message)

        previous_network = llm_net.set(self)
        try:
            async for response in agent.areceive(message):
                if (yield response) == StopIteration:
                    break
                async for response in self.areceive(response):
                    yield response
        finally:
            llm_net.reset(previous_network)
