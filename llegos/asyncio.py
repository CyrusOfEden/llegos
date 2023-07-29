from functools import partial
from typing import (
    AsyncIterable,
    Callable,
    Coroutine,
    Iterable,
    Optional,
    TypeVar,
    Union,
)

from aiometer import amap
from networkx import DiGraph
from pyee import AsyncIOEventEmitter

from llegos.ephemeral import EphemeralAgent, EphemeralMessage, Field

T = TypeVar("T", bound=EphemeralMessage)
AsyncReply = Union[Optional[T], AsyncIterable[T]]


class AsyncAgent(EphemeralAgent):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter,
        exclude=True,
        description="emitting events is non-blocking",
    )

    async def receive(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        response = getattr(self, message.intent)
        self.emit(message.intent, message)

        match response:
            case AsyncIterable():
                async for reply in response:
                    yield reply
            case Coroutine():
                reply = await response
                if reply:
                    yield reply


AsyncApplicator = Callable[[EphemeralMessage], AsyncIterable[EphemeralMessage]]


async def async_apply(message: EphemeralMessage) -> AsyncIterable[EphemeralMessage]:
    agent: Optional[AsyncAgent] = message.receiver
    if not agent:
        raise StopAsyncIteration
    async for reply_l1 in agent.receive(message):
        yield reply_l1


async def async_propogate(
    message: EphemeralMessage, applicator: AsyncApplicator = async_apply
) -> AsyncIterable[EphemeralMessage]:
    async for reply_l1 in applicator(message):
        yield reply_l1
        async for reply_l2 in async_propogate(reply_l1):
            yield reply_l2


async def async_propogate_all(
    messages: Union[Iterable[EphemeralMessage], AsyncIterable[EphemeralMessage]],
    applicator: AsyncApplicator = async_apply,
):
    if isinstance(AsyncIterable, messages):
        messages = (m async for m in messages)

    propogator = partial(async_propogate, applicator=applicator)
    async with amap(propogator, messages) as generators:
        async for gen in generators:
            async for reply_l1 in gen:
                yield reply_l1


async def async_message_graph(messages: AsyncIterable[EphemeralMessage]) -> DiGraph:
    g = DiGraph()
    async for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g
