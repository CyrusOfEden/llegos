import asyncio
from abc import ABCMeta

from eventemitter import EventEmitter
from pydantic import Field

from llambdao import AbstractObject, Message


class AbstractAsyncAgent(AbstractObject, EventEmitter, meta=ABCMeta):
    _loop: asyncio.AbstractEventLoop = Field(default_factory=asyncio.new_event_loop)

    def __init__(self, *args, **kwargs):
        super(AbstractObject, self).__init__(*args, **kwargs)
        super(EventEmitter, self).__init__(loop=self._loop)

    def is_idle(self, agent: str):
        return self.activity[agent] is None

    async def ainform(self, message: Message) -> None:
        raise NotImplementedError()

    async def arequest(self, message: Message) -> Message:
        raise NotImplementedError()


class AsyncAgentDispatcher(AbstractObject, meta=ABCMeta):
    async def register(self, name: str, agent: AbstractAsyncAgent):
        self.agents[name] = agent

    async def deregister(self, name: str):
        del self.agents[name]

    async def dispatch(self, message: Message):
        method = getattr(self.route(message), message.action)
        response = await method(message)
        return response
