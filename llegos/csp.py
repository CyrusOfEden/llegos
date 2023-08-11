"""
There's probably better ways to do this, but here's an implementation for now
"""

from janus import Queue
from sorcery import delegate_to_attr

from llegos.asyncio import AsyncBehavior, EphemeralBehavior, EphemeralMessage, Field


class Channel(EphemeralBehavior):
    _queue: Queue[EphemeralMessage] = Field(default_factory=Queue, exclude=True)

    @property
    def queue(self):
        return self._queue.sync_q

    @property
    def unfinished_tasks(self):
        return self._queue.unfinished_tasks

    (
        closed,
        empty,
        full,
        get_nowait,
        get,
        join,
        maxsize,
        put_nowait,
        put,
        qsize,
        task_done,
    ) = delegate_to_attr("queue")


class AsyncChannel(AsyncBehavior, Channel):
    @property
    def queue(self):
        return self._queue.async_q


class PutImmediate(EphemeralMessage):
    "Raises `FullError` if the channel is full."
    intent = "put_nowait"


class GetImmediate(EphemeralMessage):
    "Raises `EmptyError` if there is no message in the channel."
    intent = "get_nowait"


class GetTask(EphemeralMessage):
    "Blocks until a message is available."
    intent = "get"


class PutTask(EphemeralMessage):
    "Blocks until a message can be put in the channel."
    intent = "put"


class WaitForCompletion(EphemeralMessage):
    "Blocks until all messages in the channel have been processed."
    intent = "join"


class TaskDone(EphemeralMessage):
    "Marks the task as complete."
    intent = "task_done"
