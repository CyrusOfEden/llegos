from typing import AsyncIterable, Optional

from janus import Queue
from pydantic import Field
from pyee.asyncio import AsyncIOEventEmitter
from sorcery import delegate_to_attr

from llm_net.base import GenAgent, GenNetwork, SystemAgent, llm_net
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

        method = getattr(self, message.type)
        return method(message)


class AsyncGenNetwork(GenNetwork):
    async def areceive(self, message: Message) -> AsyncIterable[Message]:
        agent: Optional[AsyncGenAgent] = message.receiver
        if agent is None:
            return
        if agent not in self:
            raise ValueError(f"Receiver {agent.id} not in GenNetwork")

        self.emit("receive", message)

        previous_net = llm_net.set(self)
        try:
            async for response in agent.areceive(message):
                if (yield response) == StopAsyncIteration:
                    break
                async for response in self.areceive(response):
                    yield response
        finally:
            llm_net.reset(previous_net)


class AsyncGenChannel(AsyncGenAgent, SystemAgent):
    """For something more CSP-lke, use a GenChannel instead of a GenNetwork."""

    _queue: Queue[Message] = Field(default_factory=Queue, exclude=True)

    @property
    def queue(self):
        return self._queue.async_q

    @property
    def unfinished_tasks(self):
        return self._queue.unfinished_tasks

    (
        maxsize,
        closed,
        task_done,
        qsize,
        empty,
        full,
        put_nowait,
        get_nowait,
        put,
        get,
        join,
    ) = delegate_to_attr("queue")
