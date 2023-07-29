from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import AsyncIterable, Iterable

from networkx import MultiDiGraph
from sorcery import delegate_to_attr

from llegos.actors import ActorAgent, AsyncReply, EphemeralMessage, actor_propogate
from llegos.ephemeral import EphemeralObject, Field
from llegos.roles import SystemAgent


class NetworkAgent(ActorAgent):
    @property
    def network(self):
        return network_context.get()

    @property
    def relationships(self):
        return self.network.edges(self)

    def receptive_agents(self, cls: type[EphemeralMessage]):
        network = self.network
        return [
            agent
            for _, agent in network.edges(self)
            if network.has_edge(self, agent, cls)
        ]


class AgentNetwork(NetworkAgent, SystemAgent):
    graph: MultiDiGraph = Field(
        default_factory=MultiDiGraph, include=False, exclude=True
    )

    def __contains__(self, key: str | NetworkAgent) -> bool:
        match key:
            case str():
                return key in self.directory
            case NetworkAgent():
                return key in self.graph
            case _:
                raise TypeError(
                    f"lookup key must be str or AsyncGenAgent, not {type(key)}"
                )

    (
        __getitem__,
        add_edges_from,
        add_weighted_edges_from,
        edges,
        get_edge_data,
        has_edge,
        neighbors,
        nodes,
        remove_edges_from,
    ) = delegate_to_attr("graph")

    @property
    def directory(self):
        return {a.id: a for a in self.graph.nodes}

    async def receive(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        self.emit(message.intent, message)

        previous_network = network_context.set(self)
        try:
            async for reply in actor_propogate(message):
                yield reply
        finally:
            network_context.reset(previous_network)


network_context = ContextVar("llegos.networks.context", default=AgentNetwork())


class RecurrentAgentNetwork(AgentNetwork, ABC):
    hidden_state: EphemeralObject = Field()

    async def receive(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        async for l1 in super().receive(message):
            yield l1
            async for l2 in self.forward(l1):
                yield l2

    @abstractmethod
    async def forward(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        ...


class TransformerAgentNetwork(AgentNetwork, ABC):
    async def receive(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        return await self.forward(super().receive(message))

    @abstractmethod
    async def forward(
        self, messages: Iterable[EphemeralMessage]
    ) -> AsyncReply[EphemeralMessage]:
        ...
