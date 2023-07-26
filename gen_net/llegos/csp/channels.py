from janus import Queue
from sorcery import delegate_to_attr

from gen_net.agents import Field, Message, SystemAgent
from gen_net.llegos.asyncio import AsyncGenAgent


class GenChannel(SystemAgent):
    """For something more CSP-lke, use a GenChannel instead of a GenNetwork."""

    _queue: Queue[Message] = Field(default_factory=Queue, exclude=True)

    @property
    def queue(self):
        return self._queue.sync_q

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


class AsyncGenChannel(AsyncGenAgent, GenChannel):
    """For something more CSP-lke, use a GenChannel instead of a GenNetwork."""

    @property
    def queue(self):
        return self._queue.async_q
