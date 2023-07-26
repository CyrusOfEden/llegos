from functools import partial
from typing import Any, AsyncIterable, Callable, Coroutine, Optional, TypeVar, Union

from aiometer import amap
from networkx import DiGraph
from pyee import AsyncIOEventEmitter

from gen_net.sync import Field, GenAgent, Message

T = TypeVar("T", bound=Message)
AsyncGenReply = Union[Optional[T], AsyncIterable[T]]


class AsyncGenAgent(GenAgent):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter, exclude=True
    )

    async def receive(self, message: Message) -> AsyncIterable[Message]:
        response = getattr(self, message.intent)
        self.emit("receive", message)

        match response:
            case AsyncIterable():
                async for reply in response:
                    yield reply
            case Coroutine():
                reply = await response
                if reply:
                    yield reply

    async def property(self, message: Message) -> Any:
        return getattr(self, message.intent)

    async def call(self, message: Message) -> Any:
        return self.property(message)()


Applicator = Callable[[Message], AsyncIterable[Message]]


async def apply(message: Message) -> AsyncIterable[Message]:
    agent: Optional[AsyncGenAgent] = message.receiver
    if not agent:
        raise StopAsyncIteration
    response = agent.receive(message)
    async for reply_l1 in response:
        yield reply_l1


async def propogate(
    message: Message, applicator: Applicator = apply
) -> AsyncIterable[Message]:
    async for reply_l1 in applicator(message):
        yield reply_l1
        async for reply_l2 in propogate(reply_l1):
            yield reply_l2


async def propogate_all(messages: list[Message], applicator: Applicator = apply):
    mapper = partial(propogate, applicator=applicator)
    async with amap(mapper, messages) as generators:
        async for gen in generators:
            async for reply in gen:
                yield reply


async def messages_to_graph(messages: AsyncIterable[Message]) -> DiGraph:
    g = DiGraph()
    async for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g
