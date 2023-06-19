import asyncio
from abc import ABC
from typing import AsyncIterable, Dict, List

from eventemitter import EventEmitter
from pydantic import Field

from llambdao.node import GraphNode, Message, Node


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


class AsyncGraphNode(GraphNode, ABC):
    def __init__(self, graph: Dict[AsyncNode, List[AsyncNode]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)


class AsyncMapperNode(AsyncNode):
    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        for node in nodes:
            self.link(node)
            node.link(self)

    async def ado(self, message: Message) -> AsyncIterable[Message]:
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


class AsyncGroupChatNode(AsyncMapperNode):
    """
    What you'd expect out of a chat system. Every received chat message will be
    broadcasted to all nodes except the sender. In order, every node will get to
    response to the received the message.

    This Async variant is useful when you want to increase the performance of your
    IO-bound multi-agent-system.
    """

    async def achat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            async for message_j in self.ado(message_i):
                message_j.reply_to = message_i
                yield message_j
                messages.append(message_j)
