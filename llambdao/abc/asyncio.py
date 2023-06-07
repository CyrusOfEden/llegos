import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterable, Dict, List

from eventemitter import EventEmitter
from pydantic import Field

from llambdao.abc import Graph, MapReduce, Message, Node


class AsyncNode(Node, EventEmitter, ABC):
    _loop: asyncio.AbstractEventLoop = Field(default_factory=asyncio.new_event_loop)

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        super(EventEmitter, self).__init__(loop=self._loop)

    def link(self, node: "AsyncNode", **metadata):
        super().link(node, **metadata)
        self.emit("linked", node)

    def unlink(self, node: "AsyncNode"):
        super().unlink(node)
        self.emit("unlinked", node)

    async def areceive(self, message: Message):
        future = getattr(self, f"a{message.action}")(message)
        response = await asyncio.run_coroutine_threadsafe(future, self._loop)
        yield response


class AsyncGraph(Graph, ABC):
    def __init__(self, graph: Dict[AsyncNode, List[AsyncNode]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)


class AsyncMapReduce(MapReduce, AsyncNode, ABC):
    async def areceive(self, message: Message) -> AsyncIterable[Message]:
        return self._reduce(message, self._map(message))

    async def _amap(self, message: Message) -> AsyncIterable[Message]:
        sender = message.sender
        broadcast = Message(**message.dict(), sender=self)
        tasks = (
            self._loop.create_task(edge.node.areceive(broadcast))
            for edge in self.edges.values()
            if edge.node != sender
        )
        generators = await asyncio.gather(*tasks)
        for generator in generators:
            async for response in generator:
                yield response

    @abstractmethod
    async def _areduce(
        self, message: Message, messages: AsyncIterable[Message]
    ) -> AsyncIterable[Message]:
        raise NotImplementedError()


class AsyncChat(Node, ABC):
    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    async def areceive(self, message: Message):
        messages = [message]
        while message := messages.pop():
            for edge in self.edges.values():
                if edge.node == message.sender:
                    continue
                async for response in edge.node.areceive(message):
                    yield response
                    messages.append(response)
