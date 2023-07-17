from typing import AsyncIterable, Optional, Union

from pydantic import Field
from pyee.asyncio import AsyncIOEventEmitter

from llm_net.gen import GenAgent
from llm_net.message import Message


class GenAsyncAgent(GenAgent):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter, init=False
    )

    async def areceive(
        self, message: Optional[Message] = None
    ) -> Union[None, Message, AsyncIterable[Message]]:
        if message is None or message.sender == self or message.receiver != self:
            return None

        self.emit("receive", message)

        method = getattr(self, message.type) if message.type else self.call
        return method(message)
        return method(message)
