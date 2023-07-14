from pyee.asyncio import AsyncIOEventEmitter

from gpt_net.node import Field, Message, Node


class AsyncNode(Node):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter, init=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_emitter = AsyncIOEventEmitter()

    async def areceive(self, message: Message):
        if message.from_id == self.id:
            return

        method = getattr(self, message.type, None)
        if not method:
            raise AttributeError(
                f"{self.__class__.__name__} does not have a method named {message.type}"
            )

        async for self_response in method(message):
            if (yield self_response) == StopAsyncIteration:
                break
            for node in self.successors(self):
                async for link_response in node.areceive(self_response):
                    if (yield link_response) == StopAsyncIteration:
                        break
