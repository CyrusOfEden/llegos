import asyncio
from abc import ABCMeta
from typing import Dict, Optional

from eventemitter import EventEmitter
from pydantic import Field

from llambdao import AbstractObject, Entry, Message


class AbstractAsyncAgent(AbstractObject, EventEmitter, meta=ABCMeta):
    _loop: asyncio.AbstractEventLoop = Field(default_factory=asyncio.new_event_loop)

    def __init__(self, *args, **kwargs):
        super(AbstractObject, self).__init__(*args, **kwargs)
        super(EventEmitter, self).__init__(loop=self._loop)

    async def ais_idle(self, agent: str):
        return self.activity[agent] is None

    async def areceive(self, message: Message) -> Optional[Message]:
        return getattr(self, message.action)(message)

    async def ainform(self, message: Message) -> None:
        raise NotImplementedError()

    async def arequest(self, message: Message) -> Message:
        raise NotImplementedError()


class AsyncAgentDispatcher(AbstractObject, meta=ABCMeta):
    lookup: Dict[str, Entry] = Field(default_factory=dict)

    async def register(self, agent: AbstractAsyncAgent, name: str, **metadata):
        self.lookup[name] = Entry(agent, metadata)

    async def deregister(self, name: str):
        del self.lookup[name]

    async def route(self, message: Message) -> AbstractAsyncAgent:
        return self.lookup[message.recipient].agent

    async def dispatch(self, message: Message) -> Optional[Message]:
        agent = await self.route(message)
        response = await agent.areceive(message)
        return response
