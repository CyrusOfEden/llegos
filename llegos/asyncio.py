from collections.abc import AsyncGenerator, AsyncIterable, Awaitable, Iterable
from functools import partial

from beartype import beartype
from beartype.typing import Callable, Optional, TypeVar
from networkx import DiGraph
from pyee.asyncio import AsyncIOEventEmitter

from llegos.ephemeral import EphemeralMessage, EphemeralRole, Field

T = TypeVar("T", bound=EphemeralMessage)
AsyncReply = Optional[T] | AsyncIterable[T]


class AsyncRole(EphemeralRole):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter,
        description="emitting events is non-blocking",
        exclude=True,
    )

    async def send(self, message: EphemeralMessage) -> AsyncIterable[EphemeralMessage]:
        self.emit("receive", message)

        response = getattr(self, message.intent)(message)

        match response:
            case Awaitable():
                reply = await response
                if reply:
                    yield reply
            case EphemeralMessage():
                yield response
            case AsyncIterable():
                async for reply in response:
                    yield reply
            case Iterable():
                for reply in response:
                    yield reply


AsyncApplicator = Callable[[EphemeralMessage], AsyncIterable[EphemeralMessage]]


async def async_drain(messages: AsyncIterable[EphemeralMessage]):
    async for _ in messages:
        ...


@beartype
async def async_apply(message: EphemeralMessage) -> AsyncIterable[EphemeralMessage]:
    agent: Optional[AsyncRole] = message.receiver
    if not agent:
        return
    async for reply in agent.send(message):
        yield reply


@beartype
async def async_propogate(
    message: EphemeralMessage, applicator: AsyncApplicator = async_apply
) -> AsyncIterable[EphemeralMessage]:
    async for reply_l1 in applicator(message):
        yield reply_l1
        async for reply_l2 in async_propogate(reply_l1, applicator=applicator):
            yield reply_l2


@beartype
async def async_propogate_all(
    messages: Iterable[EphemeralMessage] | AsyncIterable[EphemeralMessage],
    applicator: AsyncApplicator = async_apply,
):
    if isinstance(messages, AsyncGenerator):
        messages = (m async for m in messages)

    propogator = partial(async_propogate, applicator=applicator)
    for message in messages:
        async for reply in propogator(message):
            yield reply


@beartype
async def async_message_graph(messages: AsyncIterable[EphemeralMessage]) -> DiGraph:
    g = DiGraph()
    async for message in messages:
        if message.parent:
            g.add_edge(message.parent, message)
    return g
