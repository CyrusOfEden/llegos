import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional

from llambdao.abc import Chat, Graph, MapReduce, Message, Node
from llambdao.actor import Actor


class ActorNode(Node, ABC):
    """
    Turn a node into a concurrent actor running in its own process.
    Learn more: https://docs.ray.io/en/latest/actors.html

    Can be mixed in with ActorNode to create an actor that runs in its own event loop.
    """

    def actor(self, namespace: Optional[str] = None) -> Actor:
        return Actor.options(
            namespace=namespace, name=self.id, get_if_exists=True
        ).remote(self)


class ActorGraph(Graph, ABC):
    def __init__(self, graph: Dict[ActorNode, List[ActorNode]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)


class ActorMapReduce(MapReduce, ActorNode, ABC):
    async def areceive(self, message: Message) -> Iterable[Message]:
        return self._reduce(message, self._map(message))

    async def _amap(self, message: Message) -> Iterable[Message]:
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
        self, message: Message, messages: Iterable[Message]
    ) -> Iterable[Message]:
        raise NotImplementedError()


class ActorChat(Chat):
    def receive(self, message: Message):
        """TODO: Parallelize using ray.wait"""

        messages = [message]
        while message := messages.pop():
            for edge in self.edges.values():
                if edge.node == message.sender:
                    continue
                for response in edge.node.receive(message):
                    yield response
                    messages.append(response)
