from contextvars import ContextVar
from typing import AsyncIterable, Iterable, Union

from networkx import MultiDiGraph, is_directed_acyclic_graph
from sorcery import delegate_to_attr

from gen_net.agents import AbstractObject, Field, Message, SystemAgent
from gen_net.llegos.asyncio import AsyncGenAgent, apply

llm_net = ContextVar["GenNetwork"]("llm_net.active_network")


class NetworkAgent(AsyncGenAgent):
    def network(self):
        return llm_net.get()


class GenNetwork(NetworkAgent, SystemAgent):
    graph: MultiDiGraph = Field(
        default_factory=MultiDiGraph, include=False, exclude=True
    )

    def __init__(
        self, links: dict[AsyncGenAgent, list[tuple[str, AsyncGenAgent]]], **kwargs
    ):
        super().__init__(**kwargs)
        for u, edges in links.items():
            for event, v in edges:
                self.link(u, event, v)
        assert is_directed_acyclic_graph(self.graph)

    @property
    def directory(self):
        return {a.id: a for a in self.graph.nodes}

    def __getitem__(self, key: str) -> AsyncGenAgent:
        return self.directory[key]

    def __contains__(self, key: Union[str, AsyncGenAgent]) -> bool:
        match key:
            case str():
                return key in self.directory
            case AsyncGenAgent():
                return key in self.graph.nodes
            case _:
                raise TypeError(
                    f"lookup key must be str or AsyncGenAgent, not {type(key)}"
                )

    def link(self, u: AsyncGenAgent, key: str, v: AsyncGenAgent, **attr):
        self.graph.add_edge(u, v, key=key, **attr)

    def unlink(self, u: AsyncGenAgent, key: str, v: AsyncGenAgent):
        self.graph.remove_edge(u, v, key=key)

    (nodes, edges, predecessors, successors, neighbors) = delegate_to_attr("graph")

    async def receive(self, message: Message) -> Iterable[Message]:
        self.emit("receive", message)

        previous_net = llm_net.set(self)
        try:
            async for reply in apply(message):
                if (yield reply) == StopIteration:
                    break
        finally:
            llm_net.reset(previous_net)


class RGN(GenNetwork):
    """RGN: Recurrent Generative Network"""

    hidden_state: AbstractObject = Field()

    async def receive(self, message: Message) -> Iterable[Message]:
        async for l1 in super().receive(message):
            yield l1
            async for l2 in self.forward(l1):
                yield l2

    async def forward(self, message: Message) -> Iterable[Message]:
        ...


class TGN(GenNetwork):
    """TGN: Transformer Generative Network"""

    async def receive(self, message: Message) -> AsyncIterable[Message]:
        return await self.forward(super().receive(message))

    async def forward(self, messages: Iterable[Message]) -> AsyncIterable[Message]:
        """Apply an attentional mechanism to a sequence of messages"""
        ...
