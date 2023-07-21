from typing import AsyncIterable, Optional

from pydantic import Field
from pyee.asyncio import AsyncIOEventEmitter

from llm_net.gen import GenAgent
from llm_net.message import Message

__all__ = ["AsyncIOEventEmitter", "AsyncGenAgent", "Message", "Field"]


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
