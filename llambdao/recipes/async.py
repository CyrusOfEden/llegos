from abc import ABC
from typing import Dict, List

from llambdao import Message
from llambdao.asyncio import AsyncNode
from llambdao.recipes import Chat, Graph, Router


class AsyncRouter(Router, AsyncNode):
    async def areceive(self, message: Message):
        async for response in self.edges[message.recipient.id].node.areceive(message):
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

    async def areceive(self, message: Message):
        """Graphs should implement their own receive method."""
        raise NotImplementedError()


class AsyncChat(Chat, AsyncNode):
    async def areceive(self, message: Message):
        """TODO: Not the best way"""
        messages = [message]
        while message := messages.pop():
            stop = yield message
            if stop:
                break
            self.messages.append(message)

            message = Message(**message.dict(), sender=self)
            for edge in self.edges.values():
                if edge.node == message.sender:
                    continue
                async for response in edge.node.areceive(message):
                    messages.append(response)
