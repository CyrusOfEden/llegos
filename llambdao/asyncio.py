import asyncio
from abc import ABC
from typing import Optional

from eventemitter import EventEmitter
from pydantic import Field

from llambdao import Message, Node


class AsyncNode(Node, EventEmitter, ABC):
    _loop: asyncio.AbstractEventLoop = Field(default_factory=asyncio.new_event_loop)

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        super(EventEmitter, self).__init__(loop=self._loop)

    async def alink(self, node: "AsyncNode", **metadata):
        super().link(node, **metadata)
        self.emit("linked", node)

    async def aunlink(self, node: "AsyncNode"):
        super().unlink(node)
        self.emit("unlinked", node)

    async def areceive(self, message: Message) -> Optional[Message]:
        self.emit("received", message)
        future = getattr(self, f"a{message.action}")(message)
        response = await asyncio.run_coroutine_threadsafe(future, self._loop)
        self.emit("responded", message, response)
        return response
