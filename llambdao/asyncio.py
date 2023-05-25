import asyncio
from abc import ABCMeta
from typing import Coroutine, Dict, Optional

from eventemitter import EventEmitter
from pydantic import Field

from llambdao import AbstractObject, Message, Metadata


class AsyncReceiver(meta=ABCMeta):
    async def areceive(self, message: Message) -> Optional[Message]:
        raise NotImplementedError


class AsyncNode(AbstractObject, EventEmitter, meta=ABCMeta):
    class AsyncConnection(AbstractObject):
        receiver: AsyncReceiver = Field()
        metadata: Optional[Metadata] = Field(default=None)

    id: str = Field(default_factory=lambda: str(id(object())))
    connections: Dict[str, AsyncConnection] = Field(default_factory=dict)
    _loop: asyncio.AbstractEventLoop = Field(default_factory=asyncio.new_event_loop)

    def __init__(self, *args, **kwargs):
        super(AbstractObject, self).__init__(*args, **kwargs)
        super(EventEmitter, self).__init__(loop=self._loop)

    def _submit(self, coroutine: Coroutine) -> asyncio.Future:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    async def aconnect(self, node: "AsyncNode", **metadata):
        self.connections[node.id] = self.AsyncConnection(node, metadata)
        self.emit("connected", node)

    async def adisconnect(self, node: "AsyncNode"):
        del self.connections[node.id]
        self.emit("disconnected", node)

    async def aroute(self, message: Message):
        if message.recipient == self.id:
            return self
        return self.connections[message.recipient].node

    async def areceive(self, message: Message) -> Optional[Message]:
        handler = await self.aroute(message)
        self.emit("received", message, handler)
        response = await self._submit(handler.areceive(message))
        self.emit("responded", response)
        return response
