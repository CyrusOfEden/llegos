import typing as t
from asyncio import AbstractEventLoop, Lock, get_event_loop, iscoroutine
from inspect import isasyncgen

from beartype import beartype
from beartype.typing import AsyncIterator, Callable, Optional
from pydantic import PrivateAttr

from llegos.asyncio.event_emitter import AsyncEventEmitter

from . import research as llegos
from .logger import getLogger

logger = getLogger("development")


class AsyncActor(llegos.Actor):
    _lock: Lock = PrivateAttr(default_factory=Lock)
    _loop: AbstractEventLoop = PrivateAttr(default_factory=get_event_loop)
    _event_emitter: AsyncEventEmitter = PrivateAttr(default_factory=AsyncEventEmitter)

    async def add_listener(self, event: str, f: Callable) -> None:
        await self._event_emitter.add_listener(event, f)

    async def on(self, event: str, f: Callable) -> None:
        await self._event_emitter.on(event, f)

    async def once(self, event: str, f: Callable) -> None:
        await self._event_emitter.once(event, f)

    async def remove_listener(self, event: str, f: Callable) -> None:
        await self._event_emitter.remove_listener(event, f)

    async def remove_all_listeners(self, event: str) -> None:
        await self._event_emitter.remove_all_listeners(event)

    def listeners(self, event: str) -> list[Callable]:
        return self._event_emitter.listeners(event)

    def event_names(self) -> set[str]:
        return self._event_emitter.event_names()

    async def emit(self, event: str, *args: t.Any, **kwargs: t.Any) -> bool:
        return await self._event_emitter.emit(event, *args, **kwargs)

    async def receive(self, message: llegos.Message):
        async with self._lock:
            logger.debug(f"{self.id} before:receive {message.id}")
            await self.emit("before:receive", message)

            response = self.receive_method(message)(message)

            if isasyncgen(response):
                async for message in response:
                    yield message
                return
            elif iscoroutine(response):
                response = await response

        match response:
            case llegos.Message():
                yield response
            case t.Iterable():
                for message in response:
                    yield message


class AsyncNetwork(AsyncActor, llegos.Network):
    ...


class Message(llegos.Message):
    sender: Optional[AsyncActor] = None
    receiver: Optional[AsyncActor] = None


@beartype
async def message_send(message: Message) -> AsyncIterator[Message]:
    if not message.receiver:
        raise llegos.MissingReceiver(message)
    async for message in message.receiver.receive(message):
        yield message


@beartype
async def message_propogate(
    message: Message,
    send_fn: Callable[[Message], AsyncIterator[Message]] = message_send,
) -> AsyncIterator[Message]:
    async for reply in send_fn(message):
        if reply:
            yield reply
            async for recursed_reply in message_propogate(reply, send_fn):
                yield recursed_reply
