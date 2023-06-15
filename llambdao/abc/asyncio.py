import asyncio
from abc import ABC
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


class AsyncMapReduce(MapReduce, AsyncNode):
    async def areceive(self, message: Message) -> AsyncIterable[Message]:
        return self._reduce(message, self._map(message))

    async def _amap(self, message: Message) -> AsyncIterable[Message]:
        sender = message.sender
        tasks = (
            self._loop.create_task(edge.node.areceive(message))
            for edge in self.edges.values()
            if edge.node != sender
        )
        generators = await asyncio.gather(*tasks)
        for generator in generators:
            async for response in generator:
                yield response

    async def _areduce(
        self, message: Message, messages: AsyncIterable[Message]
    ) -> AsyncIterable[Message]:
        yield message
        async for message in messages:
            yield message


class AsyncStableChat(Node):
    """
    What you'd expect out of a chat system. Every received chat message will be
    broadcasted to all nodes except the sender. In order, every node will get to
    response to the received the message.

    This Async variant is useful when you want to increase the performance of your
    IO-bound multi-agent-system.
    """

    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    async def achat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            for edge in self.edges.values():
                if edge.node == message_i.sender:
                    continue
                async for message_j in edge.node.areceive(message_i):
                    message_j.reply_to = message_i
                    yield message_j
                    messages.append(message_j)

                    message_i = message_j


class AsyncUnstableChat(Node, ABC):
    """
    Useful to have multiple nodes process a received "chat" message in parallel.
    Every received chat message will be broadcasted to all nodes except the sender.
    This is useful when you're asyncio-bound, with i.e. web requests.
    """

    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    async def achat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            futures = [
                edge.node.areceive(message_i)
                for edge in self.edges.values()
                if edge.node != message_i.sender
            ]
            for response_messages in asyncio.as_completed(futures):
                async for message_j in response_messages:
                    message_j.reply_to = message_i
                    yield message_j
                    messages.append(message_j)

                    message_i = message_j
